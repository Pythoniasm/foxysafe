# FoxySafe

[![PyPI Version](https://img.shields.io/pypi/v/foxysafe?color=blue)](https://pypi.org/project/foxysafe)
[![GitHub Tag](https://img.shields.io/github/v/tag/Pythoniasm/foxysafe?label=GitHub&color=black)](https://github.com/Pythoniasm/foxysafe)

GitLab backup tool for repositories, issues, wikis, and snippets.

## Table of Contents
- [FoxySafe](#foxysafe)
  - [Table of Contents](#table-of-contents)
  - [Install](#install)
  - [Usage](#usage)
  - [Contribute](#contribute)
    - [Development Installation](#development-installation)

## Install

```console
pip install foxysafe
```

## Usage

- Copy the `default_config.yaml` to a custom `config.yaml` and adjust the settings to your needs.
- Copy the `.env.example` to ` and adjust the settings to your needs.

If you have cloned the repository and run the package from the source directory with `default_config.yaml`:
```console
foxysafe
```

If you have cloned the repository and run the package from the source directory with a path to a custom config `PATH_TO/config.yaml`:
```console
foxysafe --config-name PATH_TO_CONFIG.yaml
```

## Contribute

### Development Installation

```console
git clone https://github.com/Pythoniasm/foxysafe.git
cd foxysafe
```

```console
python -m pip install --upgrade -e ".[dev]"
```

Further, you can use Makefile to run linting:

```console
make lint
```
