'''
Utility functions.
'''

import torch
from pytorch_lightning.callbacks.progress import TQDMProgressBar
import matplotlib.pyplot as plt
import gif

'''
Sobolev loss function, which computes the loss as a sum of the function l2 loss
and derivative l2 losses.

Input:
    pred: predictions
    x: actual values
    order: max derivative order
    lambda_r: derivative error weighting
'''
def sobolev_loss(pred, x, order=1, lambda_r=(0.25, 0.0625)):
    #setup
    bs = pred.shape[0]

    sq_shape = np.sqrt(x.shape[2]).astype(int)
    numel = sq_shape * sq_shape

    temp_x = torch.reshape(x, (x.shape[0],x.shape[1],sq_shape,sq_shape))
    temp_pred = torch.reshape(pred, (pred.shape[0],pred.shape[1],sq_shape,sq_shape))

    #compute function l1 error
    loss = torch.sum((temp_pred-temp_x)**2)

    #compute derivatives l1 error
    stencil = torch.tensor([[0.0, -1.0, 0.0],[-1.0, 4.0, -1.0],[0.0, -1.0, 0.0]], device=x.device)*1/4
    stencil = torch.reshape(stencil, (1,1,3,3)).repeat(1, x.shape[1], 1, 1)

    for i in range(order):
        temp_x = torch.nn.functional.conv2d(temp_x, stencil)
        temp_pred = torch.nn.functional.conv2d(temp_pred, stencil)

        loss += lambda_r[i] * torch.sum((temp_pred-temp_x)**2)

    return loss/bs

'''
Makes a GIF of the model output on the test data provided by the data module and
saves it to the appropriate lightning log.

Input:
    trainer: lightning trainer
    data_module: data module
    model: model to use, or if None then use best saved model
'''
def make_gif(trainer, data_module, model=None):
    #run on test data
    results = trainer.predict(model, datamodule=data_module)

    #transform data back to regular form
    data = data_module.aglomerate(results)

    #if multichannel then just take first channel
    if data.dim() > data_module.dimension+1:
        data = data[...,0]

    #gif frame closure
    @gif.frame
    def plot(i):
        plt.imshow(data[i,:,:], vmin=-1, vmax=1, origin='lower')
        plt.colorbar(location='top')

    #build frames
    frames = [plot(i) for i in range()]

    #save gif
    gif.save(frames, f'{trainer.logger.log_dir}/train.gif', duration=50)

'''
Custom PT Lightning training progress bar.
'''
class ProgressBar(TQDMProgressBar):
    def __init__(self):
        super().__init__()
