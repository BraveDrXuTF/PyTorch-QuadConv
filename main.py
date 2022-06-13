'''
Builds and trains a model based on input parameters, which can be specified via
command line arguments or an experiment YAML file.

Example usage:

- Run the test found in experiments/ignition.yml
    python main.py --experiment ignition
'''

from core.model import AutoEncoder
from core.data import PointCloudDataModule, GridDataModule
from core.utilities import ProgressBar, make_gif

from argparse import ArgumentParser
import yaml
import torch
from pytorch_lightning import Trainer, LightningDataModule
from pytorch_lightning.callbacks import ModelCheckpoint, EarlyStopping

'''
Build and train a model.

Input:
    trainer_args: PT Lightning Trainer arguments
    model_args: QCNN or CNN model arguments
    data_args: dataset arguments
    extra_args: other arguments that don't fit in groups above
'''
def main(trainer_args, model_args, data_args, extra_args):
    torch.set_default_dtype(torch.float32)

    #Setup data
    data_module = GridDataModule(**data_args)
    model_args['input_shape'] = data_module.get_shape()

    #Build model
    model = AutoEncoder(**model_args)

    #callbacks
    callbacks=[ProgressBar()]
    if extra_args['early_stopping']:
        callbacks.append(EarlyStopping(monitor="val_loss", patience=3, strict=False))
    if train_args['enable_checkpointing']:
        callbacks.append(ModelCheckpoint(monitor="val_loss", save_last=True, save_top_k=1, mode='min'))

    #train model
    trainer = Trainer(**train_args, callbacks=callbacks)
    trainer.fit(model=model, datamodule=data_module, ckpt_path=None)

    #make GIF
    if extra_args['make_gif']:
        m = None if train_args['enable_checkpointing'] else model
        make_gif(trainer, data_module, m)

'''
Parse arguments
'''
if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--experiment", type=str, default=None, help="Named experiment")
    args, _ = parser.parse_known_args()

    #use CL config
    if args.experiment == None:
        train_parser = ArgumentParser()
        model_parser = ArgumentParser()
        data_parser = ArgumentParser()
        extra_parser = ArgumentParser()

        #trainer args
        train_parser = Trainer.add_argparse_args(train_parser)

        #model specific args
        model_parser = AutoEncoder.add_args(model_parser)

        #data specific args
        data_parser = PointCloudDataModule.add_args(data_parser)

        #extra args
        extra_parser.add_argument("--make_gif", type=bool, default=False)
        extra_parser.add_argument("--early_stopping", type=bool, default=False)

        #parse remaining args
        train_args, _ = train_parser.parse_known_args()
        model_args, _ = model_parser.parse_known_args()
        data_args, _ = data_parser.parse_known_args()
        extra_args, _ = extra_parser.parse_known_args()

        #convert to dictionaries
        train_args, model_args, data_args, extra_args = vars(train_args), vars(model_args), vars(data_args), vars(extra_args)

    #use YAML config
    else:
        try:
            #open YAML file
            with open(f"experiments/{args.experiment}.yml", "r") as file:
                config = yaml.safe_load(file)

            #extract args
            train_args, model_args, data_args, extra_args = config['train'], config['model'], config['data'], config['extra']

        except Exception as e:
            raise ValueError(f"Experiment {args.experiment} is invalid.")

    main(train_args, model_args, data_args, extra_args)
