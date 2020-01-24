"""
A command line parser to run an attack from user specifications.
"""

import os
import textattack
import time
import torch
import tqdm

from textattack_args_helper import *

def set_env_variables(gpu_id):
    # Only use one GPU, if we have one.
    if 'CUDA_VISIBLE_DEVICES' not in os.environ:
        os.environ['CUDA_VISIBLE_DEVICES'] = str(gpu_id)
    # Disable tensorflow logs, except in the case of an error.
    if 'TF_CPP_MIN_LOG_LEVEL' not in os.environ:
        os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
    # Cache TensorFlow Hub models here, if not otherwise specified.
    if 'TFHUB_CACHE_DIR' not in os.environ:
        os.environ['TFHUB_CACHE_DIR'] = os.path.expanduser('~/.cache/tensorflow-hub')

def get_model_and_attack(args):
    # Models
    model = parse_model_from_args(args)
    # Attack
    attack = parse_attack_from_args(model, args)
    return model, attack

def attack_from_queue(args, in_queue, out_queue):
    # @TODO make this work with something like:
    # `CUDA_VISIBLE_DEVICES=2,3`.
    gpu_id = torch.multiprocessing.current_process()._identity[0] - 2
    print('using GPU #' + str(gpu_id))
    set_env_variables(gpu_id)
    model, attack = get_model_and_attack(args)
    while not in_queue.empty():
        try: 
            label, text = in_queue.get()
            results_gen = attack.attack_dataset([(label, text)], num_examples=1)
            result = next(results_gen)
            out_queue.put(result)
        except Exception as e:
            print('process on GPU', gpu_id, 'got exception:', e)
            # done!
            return

# @TODO make this work with `attack_n`
def main():

    pytorch_multiprocessing_workaround()
    # This makes `args` a namespace that's sharable between 
    args = torch.multiprocessing.Manager().Namespace(
        **vars(get_args())
    )
    start_time = time.time()
    
    attack_logger = parse_logger_from_args(args)
    
    num_gpus = torch.cuda.device_count()
    dataset = DATASET_BY_MODEL[args.model](offset=args.num_examples_offset)
    
    print(f'Running on {num_gpus} GPUs')
    load_time = time.time()

    if args.interactive:
        raise RuntimeException('Cannot run in parallel if --interactive set')
    
    pbar = tqdm.tqdm(total=args.num_examples)
    def update_pbar(*_):
        print('UPDATE PBAR?')
        pbar.update(1)
    
    in_queue = torch.multiprocessing.Queue()
    out_queue =  torch.multiprocessing.Queue()
    # Add stuff to queue.
    for _ in range(args.num_examples):
        label, text = next(dataset)
        in_queue.put((label, text))
    # Start workers.
    pool = torch.multiprocessing.Pool(
        num_gpus, 
        attack_from_queue, 
        (args, in_queue, out_queue)
    )
    # Log results asynchronously.
    num_results = 0
    while num_results < args.num_examples:
        result = out_queue.get(block=True)
        attack_logger.log_result(result)
        pbar.update()
        num_results += 1
    pbar.close()
    print()
    # Enable summary stdout
    attack_logger.enable_stdout()
    print()
    attack_logger.log_summary()
    print()
    finish_time = time.time()
    print(f'Attack time: {time.time() - load_time}s')

def pytorch_multiprocessing_workaround():
    # This is a fix for a known bug
    try:
        torch.multiprocessing.set_start_method('spawn')
    except RuntimeError:
        pass


if __name__ == '__main__': main()