

## Usage

```sh
./scripts/main.py
```

```sh
usage: main.py [-h] [--src SRC] [--tgt_coords TGT_COORDS] [--tgt_segs TGT_SEGS] [--tamp TAMP] [--tgt TGT]

Process transport record and update map HTML.

options:
  -h, --help            show this help message and exit
  --src SRC             Path to the source transport record file.
  --tgt_coords TGT_COORDS
                        Path to the location coordinates file.
  --tgt_segs TGT_SEGS   Path to the travel segments file.
  --tamp TAMP           Path to the template HTML file.
  --tgt TGT             Path to the target HTML file.
```


Then, check `./incoming.html`. Afterwards,

```sh
mv incoming.html index.html
```

Donnot forget `git commit` and `push`.
