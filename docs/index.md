## Quickstart

### Introduction

TODO

### Installing ROHE

ROHE currently supports Python 3.10 and above.

#### Pip

We recommend creating a virtual environment for your project when installing ROHE.

For more information on setting up a virtual environment, see the
[official Python documentation for virtual environments](https://docs.python.org/3/library/venv.html).

Once you have your environment set up, you can install the latest version of ROHE with:

```bash
pip install rohe
```

#### Conda

We currently haven't supported installing from conda yet

### Example

TODO

## Architecture

### High-level view

<figure>
<p style="text-align:center">
<img src="img/animated.svg" alt="ROHE High-level View" width="1000"/>
</p>
</figure>

### Orchestration

TODO

### Observation

TODO

## Enable rohe-cli auto-completion

=== "Bash"

    Save the script somewhere.
    ```bash
    _ROHE_CLI_COMPLETE=bash_source rohe-cli > ~/.rohe-cli-complete.bash
    ```
    Source the file in ~/.bashrc.
    ```bash
    source ~/.foo-bar-complete.bash
    ```

=== "Zsh"

    Save the script somewhere.
    ```bash
    _ROHE_CLI_COMPLETE=zsh_source rohe-cli > ~/.rohe-cli-complete.zsh
    ```
    Source the file in ~/.zshrc.
    ```bash
    source ~/.rohe-cli-complete.zsh
    ```

=== "Fish"

    Save the script to ~/.config/fish/completions/rohe-cli.fish:
    ```fish
    _ROHE_CLI_COMPLETE=fish_source rohe-cli > ~/.config/fish/completions/rohe-cli.fish
    ```

## Reference

If you use the software, you can cite

```

@software{site:rohe,
author = {Minh-Tri Nguyen and Hong-Linh Truong},
license = {Apache-2.0},
month = Dec,
title = {{ROHE: An Orchestration Framework for End-to-End Machine Learning Serving with Resource Optimization on Heterogeneous Edge}},
url = {https://github.com/rdsea/ROHE},
year = {2023}
}

```

## Authors/Contributors

- Minh-Tri Nguyen
- Hong-Linh Truong
- Vuong Nguyen
- Anh-Dung Nguyen
