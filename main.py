'''
Builds, trains, and tests an autoencoder model based on input parameters, which
are specified via a YAML configuration file and optional command line arguments.

Example usage:
    - Run the test found in experiments/tests/test.yaml
        python main.py --experiment tests/test.yaml
'''

import argparse
import yaml
import os
import platform
from pathlib import Path

import torch
from pytorch_lightning import Trainer
from pytorch_lightning.callbacks import ModelCheckpoint, EarlyStopping

from core.autoencoder import AutoEncoder
from core.structured_data import GridDataModule
from core.utilities import Logger, make_gif

'''
Build, train, and test a model.

Input:
    experiment: experiment name
    trainer_args: PT Lightning Trainer arguments
    model_args: QCNN or CNN model arguments
    data_args: dataset arguments
    misc_args: miscellaneous arguments
'''
def main(experiment, trainer_args, model_args, data_args, misc_args):
    #setup datamodule
    datamodule = GridDataModule(**data_args)
    model_args['input_shape'] = datamodule.get_shape()

    #build model
    model = AutoEncoder(**model_args)

    #callbacks
    callbacks=[]
    if trainer_args['enable_checkpointing']:
        callbacks.append(ModelCheckpoint(monitor="val_err",
                                            save_last=True,
                                            save_top_k=1,
                                            mode='min',
                                            filename='{epoch}'))
    if misc_args['early_stopping']:
        callbacks.append(EarlyStopping(monitor="val_err",
                                        patience=5,
                                        strict=False))

    #logger
    if trainer_args['logger']:
        #save the configuration details
        exp_dir, exp_name = os.path.split(experiment)
        exp_name = os.path.splitext(exp_name)[0]

        logger = Logger(save_dir=os.path.join(trainer_args['default_root_dir'], exp_dir),
                        name=exp_name, default_hp_metric=False)

        filename = os.path.join(logger.log_dir, 'config.yaml')
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, "w") as file:
            yaml.dump(config, file)

        #add logger to trainer args
        trainer_args['logger'] = logger

    #build trainer
    trainer = Trainer(**trainer_args, callbacks=callbacks)

    #
    #NOTE: When I tried to implement this, it wasn't working, not a major
    #priority, but something to figure out
    # if trainer_args['auto_scale_batch_size']:
    #     trainer.tune(model, datamodule=datamodule)

    #train model
    trainer.fit(model=model, datamodule=datamodule, ckpt_path=None)

    #make GIF
    if misc_args['make_gif']:
        make_gif(trainer, datamodule, None if trainer_args['enable_checkpointing'] else model)

    #compute testing statistics
    if misc_args['compute_stats']:
        trainer.test(model=None if trainer_args['enable_checkpointing'] else model,
                        ckpt_path='best' if trainer_args['enable_checkpointing'] else None,
                        datamodule=datamodule)

    return 

'''
Parse arguments from configuration file and command line. Command line arguments
will override their config file counterparts.
'''
if __name__ == "__main__":
    #windows setup
    if platform.system() == 'Windows':
        os.environ['PL_TORCH_DISTRIBUTED_BACKEND'] = 'gloo'

    #look for config
    parser = argparse.ArgumentParser()
    parser.add_argument("--experiment", type=str, default=None, help='YAML configuration file path relative to ./experiments with or without extension.')
    experiment = vars(parser.parse_known_args()[0])['experiment']

    #load YAML config
    if experiment != None:
        try:
            exp_path = list(Path('experiments/').rglob(experiment + '*'))

            if len(exp_path) != 1:
                raise ValueError('Experiment was not uniquely specified')

            #open YAML file
            with exp_path[0].open() as file:
                config = yaml.safe_load(file)

            #extract args
            trainer_args = config['train']
            model_args = config['model']
            data_args = config['data']
            misc_args = config['misc']

        except Exception as e:
            raise ValueError(f"Experiment {experiment} is invalid.")

    else:
        raise ValueError("An experiment configuration file must be provided.")

    #trainer args
    trainer_parser = argparse.ArgumentParser(argument_default=argparse.SUPPRESS)
    trainer_parser.add_argument("--default_root_dir", type=str)
    trainer_parser.add_argument("--max_time", type=str)

    #model specific args
    model_parser = argparse.ArgumentParser(argument_default=argparse.SUPPRESS)
    model_parser = AutoEncoder.add_args(model_parser)

    #data specific args
    data_parser = argparse.ArgumentParser(argument_default=argparse.SUPPRESS)
    data_parser = GridDataModule.add_args(data_parser)

    #look for other CL arguments
    trainer_args.update(vars(trainer_parser.parse_known_args()[0]))
    model_args.update(vars(model_parser.parse_known_args()[0]))
    data_args.update(vars(data_parser.parse_known_args()[0]))

    #run main script
    main(experiment, trainer_args, model_args, data_args, misc_args)
