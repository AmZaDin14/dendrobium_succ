{ pkgs, config, lib, ... }:

let
  # Python 3.11 with C-extension ML/scientific deps pre-built from nixpkgs.
  # Pure-Python deps (typer, rich, modal) and predict deps (torch 2.1.1,
  # torchrl, tensordict, protlearn) come from `uv sync` via pyproject.toml.
  # Using 3.11 because torch 2.1.x (pinned to match bundled models) has
  # no wheels for Python ≥ 3.12.
  pyEnv = pkgs.python311.withPackages (ps: with ps; [
    scikit-learn
    matplotlib
    biopython
  ]);
in {
  # ---------------------------------------------------------------------------
  # Python
  # ---------------------------------------------------------------------------
  languages.python = {
    enable = true;
    package = pyEnv;
  };

  # ---------------------------------------------------------------------------
  # Extra system packages
  # ---------------------------------------------------------------------------
  packages = with pkgs; [
    uv
    git
    stdenv.cc.cc.lib  # libstdc++ runtime for C extensions
    zlib              # libz.so.1 — needed by PyPI numpy/manylinux wheels
  ];

  # ---------------------------------------------------------------------------
  # Environment variables
  # ---------------------------------------------------------------------------
  env = {
    PYTHONUNBUFFERED         = "1";
    PYTHONDONTWRITEBYTECODE  = "1";
    UV_LINK_MODE             = "copy";
    LD_LIBRARY_PATH          = "${pkgs.stdenv.cc.cc.lib}/lib:${pkgs.zlib}/lib";
  };

  # ---------------------------------------------------------------------------
  # No `processes` block — this is a CLI tool, not a long-running service.
  # Use `dendrobium-succ <cmd>` (venv is activated) or `uv run dendrobium-succ <cmd>`.
  # ---------------------------------------------------------------------------

  # ---------------------------------------------------------------------------
  # Shell hook — recreate uv venv pointing to nixpkgs Python, then activate.
  # ---------------------------------------------------------------------------
  enterShell = ''
    # Rebuild venv if nixpkgs Python changed (or venv doesn't exist yet)
    NEEDS_REBUILD=0
    if [ ! -x .venv/bin/python ]; then
      NEEDS_REBUILD=1
    elif [ "$(readlink -f .venv/bin/python 2>/dev/null)" != "${pyEnv}/bin/python" ]; then
      NEEDS_REBUILD=1
    fi
    if [ "$NEEDS_REBUILD" = "1" ]; then
      echo "[devenv] (re)creating .venv with nixpkgs python…"
      rm -rf .venv
      uv venv \
        --python ${pyEnv}/bin/python \
        --system-site-packages \
        .venv
    fi

    # Activate venv for this shell
    export VIRTUAL_ENV="$PWD/.venv"
    export PATH="$VIRTUAL_ENV/bin:$PATH"
    export PYTHONPATH="$PWD''${PYTHONPATH:+:$PYTHONPATH}"

    # Install pyproject deps (and dev group) if pyproject.toml changed
    if [ ! -f .venv/.deps_installed ] || [ pyproject.toml -nt .venv/.deps_installed ]; then
      echo "[devenv] Running uv sync (pyproject deps + dev group)…"
      uv sync --group dev
      touch .venv/.deps_installed
    fi

    echo ""
    echo "  dendrobium_succ dev environment ready"
    echo "  ── dendrobium-succ <cmd>          (venv is active on PATH)"
    echo "  ── uv run dendrobium-succ <cmd>   (same, with uv run)"
    echo "  ── uv run pytest                  (run tests)"
    echo "  ── bash scripts/demo.sh           (end-to-end demo)"
    echo ""
    echo "  Single Python 3.11 venv. All deps (including torch 2.1.1,"
    echo "  torchrl, tensordict, protlearn) come from uv sync."
    echo ""
  '';
}
