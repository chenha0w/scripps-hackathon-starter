#!/bin/bash
# hello_hpc.slurm — your first job on Garibaldi.
#
# Submit it from a login node with:
#   sbatch hello_hpc.slurm
#
# Then check progress:
#   squeue -u $USER
#   cat hello_hpc_*.out
#
# This job asks for a tiny amount of resources so it should start almost
# immediately. If it stays "PD" (pending) for more than a minute or two,
# the partition is busy — try `squeue -u $USER --start` for an ETA.

#SBATCH --job-name=hello_hpc
#SBATCH --partition=shared
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=512M
#SBATCH --time=00:05:00
#SBATCH --output=hello_hpc_%j.out
#SBATCH --error=hello_hpc_%j.err

cd "$SLURM_SUBMIT_DIR"

echo "=============================================="
echo "Hello from Garibaldi!"
echo "=============================================="
echo "User           : $(whoami)"
echo "Host           : $(hostname)"
echo "Date           : $(date)"
echo "Working dir    : $(pwd)"
echo "Job ID         : $SLURM_JOB_ID"
echo "Job name       : $SLURM_JOB_NAME"
echo "Partition      : $SLURM_JOB_PARTITION"
echo "Nodes assigned : $SLURM_JOB_NODELIST"
echo "CPUs per task  : $SLURM_CPUS_PER_TASK"
echo "----------------------------------------------"

# Show a few cluster facts so you know the environment is real.
echo "Cluster modules available:"
module av || true

echo "----------------------------------------------"
echo "If you can read this in hello_hpc_${SLURM_JOB_ID}.out,"
echo "your HPC setup is working end-to-end. Nice work."
