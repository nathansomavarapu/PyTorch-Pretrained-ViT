"""utils.py - Helper functions
"""

import torch
from torch.utils import model_zoo

from .configs import PRETRAINED_MODELS


def load_pretrained_weights(
    model, 
    model_name, 
    weights_path=None, 
    load_first_conv=True, 
    load_fc=True, 
    resize_positional_embedding=False,
    image_size=None,
    verbose=True
):
    """Loads pretrained weights from weights path or download using url.

    Args:
        model (Module): The whole model of efficientnet.
        model_name (str): Model name of efficientnet.
        weights_path (None or str):
            str: path to pretrained weights file on the local disk.
            None: use pretrained weights downloaded from the Internet.
        load_fc (bool): Whether to load pretrained weights for fc layer at the end of the model.
        verbose (bool): Whether to print on completion
    """
    
    # Load or download weights
    if weights_path is None:
        state_dict = model_zoo.load_url(PRETRAINED_MODELS[model_name]['url'])
    else:
        state_dict = torch.load(weights_path)
    

    # Modify state dict
    expected_missing_keys = []
    if not load_first_conv:
        expected_missing_keys += ['patch_embedding.weight', 'patch_embedding.bias']
    if not load_fc:
        expected_missing_keys += ['fc.weight', 'fc.bias']
    for key in expected_missing_keys:
        state_dict.pop(key)

    # Change size of positional embeddings
    if resize_positional_embedding: 
        state_dict['positional_embedding.pos_embedding'] = resize_positional_embedding_(
            posemb=state_dict['positional_embedding.pos_embedding'],
            posemb_new=model.state_dict()['positional_embedding.pos_embedding']
        )

    
    # Load state dict
    ret = model.load_state_dict(state_dict, strict=False)


    if load_fc:
        ret = model.load_state_dict(state_dict, strict=False)
        assert not ret.missing_keys, 'Missing keys when loading pretrained weights: {}'.format(ret.missing_keys)
    else:
        state_dict.pop('fc.weight')
        state_dict.pop('fc.bias')
        ret = model.load_state_dict(state_dict, strict=False)
        assert set(ret.missing_keys) == set(
            ['fc.weight', 'fc.bias']), 'Missing keys when loading pretrained weights: {}'.format(ret.missing_keys)
    assert not ret.unexpected_keys, 'Missing keys when loading pretrained weights: {}'.format(ret.unexpected_keys)
    
    if verbose:
        print('Loaded pretrained weights for {}'.format(model_name))


def as_tuple(x):
    return x if isinstance(x, tuple) else (x, x)


def resize_positional_embedding_(posemb, posemb_new):
    """Rescale the grid of position embeddings in a sensible manner"""
    from scipy.ndimage import zoom

    # Deal with class token
    ntok_new = posemb_new.shape[1]
    if hasattr(model, 'class_token'):  # this means classifier == 'token'
        posemb_tok, posemb_grid = posemb[:, :1], posemb[0, 1:]
        ntok_new -= 1
    else:
        posemb_tok, posemb_grid = posemb[:, :0], posemb[0]

    # Get old and new grid sizes
    gs_old = int(np.sqrt(len(posemb_grid)))
    gs_new = int(np.sqrt(ntok_new))
    logger.info('load_pretrained: grid-size from %s to %s', gs_old, gs_new)
    posemb_grid = posemb_grid.reshape(gs_old, gs_old, -1)

    # Rescale grid
    zoom = (gs_new / gs_old, gs_new / gs_old, 1)
    posemb_grid = zoom(posemb_grid, zoom, order=1)
    posemb_grid = posemb_grid.reshape(1, gs_new * gs_new, -1)

    # Deal with class token and return
    posemb = torch.cat([posemb_tok, posemb_grid], dim=1)
    return posemb
