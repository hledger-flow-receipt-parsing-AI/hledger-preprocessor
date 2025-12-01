# C. How to get started with hledger-flow import

Assumes you looked at [manuals/B_using_hledger.md](manuals/B_using_hledger.md).

This pip `hledger_preprocessor` pip package uses/is normally called by a
mod/fork of the `hledger-flow`. This page describes how to install that custom
fork of `hledger-flow`.

## C.1 Install haskall tools to build the hledger-flow fork locally

0. Install [stack](https://docs.haskellstack.org/en/stable/):

```sh
curl -sSL https://get.haskellstack.org/ | sh
```

1. Install prerequiesite package:

```sh
sudo apt-get install libgmp-dev
```

2. Verify haskall software package `stack` works.

```sh
stack --version
# Which should output something like: Version 3.3.1, Git revision etc.
```

3. Build the repo with:

```sh
stack test --interleaved-output --pedantic
stack install
```

4. Add to path

```sh
echo 'export PATH=$PATH:~/.local/bin' >> ~/.bashrc
source ~/.bashrc
```

### C.2 Clone the hledger-flow fork and build it locally

5. Clone the repo and enter it.

```sh
git clone git@github.com:a-t-0/hledger-flow.git
cd hledger-flow
```

6. Build fork of `hledger flow` using [these](https://github.com/apauley/hledger-flow/blob/master/CONTRIBUTING.org#build-the-project) build instructions:

```sh
chmod +x bin/build-and-test
./bin/build-and-test
# Which should end in something like:
# Copied executables to ~/.local/bin:
# - hledger-flow
```

7. Verify hledger-flow is available with:

```sh
hledger-flow --version
# Which should output something like:
# hledger-flow 0.15.0 linux x86_64 ghc 9.4 0ba2e3132217b27addedae6a579d01b0cad61a21
```

## C.3 OLD ALTERNATIVE: Importing CSV files (WITHOUT AUTOMATION!)

**These instructions are included for completeness, skip them. They are only
relevant if the pull request of the fork gets merged into the original code.**
Download [the tar](https://github.com/apauley/hledger-flow/releases).
Unpack it.
Add it the executable in the unpacked folder to your path by adding it to bashrc:

```sh
export PATH="~/finance/hledger-flow/hledger-flow_Linux_x86_64_v0.15.0_2b025fe:$PATH"
```

Reload `~/.bashrc` with:

```sh
source ~/.bashrc
```

Use it with:

```sh
hledger-flow import
```
