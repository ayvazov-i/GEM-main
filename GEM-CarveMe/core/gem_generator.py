"""
GEM reconstruction wrapper (CarveMe stub).

For the MVP, the primary path is to upload a pre-built SBML model.
CarveMe integration is provided as an optional advanced feature.
"""
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import cobra
import cobra.io

# Ensure the project bin/ directory (diamond, prodigal) is always on PATH
# when subprocesses are spawned — even if the venv was not shell-activated.
_PROJECT_BIN = str(Path(__file__).parent.parent / "bin")
if _PROJECT_BIN not in os.environ.get("PATH", ""):
    os.environ["PATH"] = _PROJECT_BIN + os.pathsep + os.environ.get("PATH", "")


def is_carveme_available() -> bool:
    """Check whether the CarveMe CLI (carve) is resolvable on PATH."""
    return shutil.which("carve") is not None


def generate_gem_from_genome(
    genome_path: str,
    gram: str = "negative",
    output_dir: str | None = None,
) -> cobra.Model:
    """
    Wrap CarveMe to auto-generate a draft GEM from an annotated genome.

    Parameters
    ----------
    genome_path : path to a .gbk or .fasta genome file
    gram : 'negative' or 'positive'
    output_dir : directory to write the SBML output; uses a temp dir if None

    Returns
    -------
    A COBRApy Model loaded from the CarveMe output.

    Raises
    ------
    RuntimeError if CarveMe is not installed or the reconstruction fails.
    FileNotFoundError if genome_path does not exist.
    """
    if not is_carveme_available():
        raise RuntimeError(
            "CarveMe is not installed or not found in PATH. "
            "Please install CarveMe and its dependencies (Diamond, Prodigal), "
            "or upload a pre-built SBML model instead."
        )

    if not Path(genome_path).exists():
        raise FileNotFoundError(f"Genome file not found: {genome_path}")

    if output_dir is None:
        tmp = tempfile.mkdtemp()
        output_path = os.path.join(tmp, "draft_gem.xml")
    else:
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, "draft_gem.xml")

    universe = "grampos" if gram == "positive" else "gramneg"

    # Detect nucleotide FASTA — requires --dna so CarveMe runs Prodigal first.
    # GenBank files (.gbk/.gb) are handled automatically without the flag.
    nucleotide_exts = {".fna", ".fasta", ".fa"}
    is_nucleotide_fasta = Path(genome_path).suffix.lower() in nucleotide_exts

    cmd = ["carve", genome_path, "-o", output_path, "-u", universe]
    if is_nucleotide_fasta:
        cmd.append("--dna")

    # Use Popen + communicate() instead of subprocess.run(capture_output=True)
    # to avoid pipe buffer deadlock on large CarveMe outputs (Windows / large genomes).
    # communicate() reads stdout and stderr concurrently, so the OS pipe never fills.
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        stdout, stderr = proc.communicate(timeout=1800)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.communicate()
        raise RuntimeError(
            "CarveMe timed out after 30 minutes. "
            "The genome may be too large, or Diamond/Prodigal may have stalled. "
            "Check that the genome file is valid."
        )
    if proc.returncode != 0:
        raise RuntimeError(
            f"CarveMe failed (exit code {proc.returncode}):\n"
            f"STDOUT: {stdout}\n"
            f"STDERR: {stderr}"
        )

    if not Path(output_path).exists():
        raise RuntimeError(f"CarveMe did not produce an output file at {output_path}.")

    model = cobra.io.read_sbml_model(output_path)
    model.id = Path(genome_path).stem + "_draft"
    return model


def load_model_from_sbml(path: str) -> cobra.Model:
    """Load a COBRApy model from an SBML (.xml) file."""
    return cobra.io.read_sbml_model(path)


def save_model_to_sbml(model: cobra.Model, path: str) -> None:
    """Write a COBRApy model to an SBML file."""
    cobra.io.write_sbml_model(model, path)
