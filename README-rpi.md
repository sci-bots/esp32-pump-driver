<!-- vim-markdown-toc GFM -->

* [Install (Raspberry Pi)](#install-raspberry-pi)
    * [Install `Berryconda3`](#install-berryconda3)
    * [Create Conda UI development environment](#create-conda-ui-development-environment)
    * [Install asyncserial:](#install-asyncserial)
    * [Clone `esp32-pump-driver`](#clone-esp32-pump-driver)
    * [Launch Jupyter notebook](#launch-jupyter-notebook)
* [Known issues](#known-issues)
    * [Jupyter Lab fails to build labextension for IPython widget](#jupyter-lab-fails-to-build-labextension-for-ipython-widget)

<!-- vim-markdown-toc -->

# Install (Raspberry Pi)

## Install `Berryconda3`

Download and install `Berryconda3`: https://github.com/jjhelmus/berryconda#quick-start

## Create Conda UI development environment

Start a terminal and run the following:

```sh
source activate
conda create -n esp32-pump -c conda-forge -c sci-bots nodejs astroid ecdsa isort lazy-object-proxy mccabe pylint pyserial typing websocket-client pyserial six jupyter notebook jupyterlab jupytext autopep8 ipywidgets pyaes
source activate esp32-pump
pip install mpy-repl-tool
python -m there.jupyter-setup
conda config --env --append channels conda-forge
```

## Install asyncserial:
```
source activate esp32-pump
cd ~
pip install trollius "ipython>=7"
git clone https://github.com/sci-bots/asyncserial
cd asyncserial
pip install .
cd ..
```

## Clone `esp32-pump-driver`

```
source activate esp32-pump
cd ~
git clone https://github.com/sci-bots/esp32-pump-driver
```

## Launch Jupyter notebook

```
source activate esp32-pump
cd ~/esp32-pump-driver
jupyter notebook
```

# Known issues

## Jupyter Lab fails to build labextension for IPython widget

Use `jupyter notebook` instead!
