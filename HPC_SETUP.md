# HPC Setup for the Scripps Research 2026 Hackathon

End-to-end instructions for getting onto the Scripps **Garibaldi** HPC
cluster and using Claude Code's `scripps-garibaldi-hpc` skill to help you
run jobs there.

By the end of this guide you'll be able to:

- SSH into Garibaldi as yourself
- Submit a tiny "hello world" Slurm job and see its output
- Have Claude generate cluster-correct `sbatch` scripts on your behalf

> **First time on an HPC cluster?** Don't worry. The cluster is just a
> bunch of shared Linux computers ("compute nodes") that you submit jobs
> to through a scheduler called **Slurm**. You log in to a small entry
> machine ("login node") and ask Slurm to run your work elsewhere. The
> golden rule: **never run heavy work directly on the login node** — it's
> shared with everyone, and abusing it will get your account flagged.

---

## 1. Request an HPC account

Garibaldi requires a Scripps email account (`@scripps.edu`) and a Unix
identity already provisioned in Active Directory.

If you don't yet have an HPC account, email **`hpc@scripps.edu`** and
ask them to enable Garibaldi access. Include:

- Your Scripps username (the part before `@scripps.edu`)
- That you're participating in the 2026 CBB Hackathon (May 29 – June 1)

Allow at least a day for the request — do this **before** the hackathon
weekend if you can.

---

## 2. Log in

There are two login hosts. Either works; if one is sluggish, try the
other:

- `garibaldi.scripps.edu`
- `login02.scripps.edu`

### macOS / Linux / WSL

```bash
ssh <your-scripps-username>@garibaldi.scripps.edu
```

Enter your Scripps password when prompted. You'll land in your home
directory (`/gpfs/home/<username>` or similar).

### Windows (native PowerShell)

OpenSSH ships with Windows 10+:

```powershell
ssh <your-scripps-username>@garibaldi.scripps.edu
```

If you'd rather use a GUI, **MobaXterm** or **PuTTY** also work fine.

### Off-campus?

You may need the Scripps VPN before SSH will connect. Check with IT if
you can't reach the host from outside the network.

---

## 3. Confirm you're on Garibaldi

Once logged in, sanity-check the environment:

```bash
hostname                  # should contain "garibaldi" or "login02"
sinfo                     # lists partitions like 'shared' and 'gpu'
squeue -u $USER           # shows your jobs (empty for now)
module av                 # peek at what software is available
```

If `sinfo` and `squeue` work, Slurm is happy and you're ready to
submit jobs.

---

## 4. Submit the "hello world" job

This repo ships with a tiny test script at
[hello-world/hello_hpc.slurm](hello-world/hello_hpc.slurm). Copy it
to the cluster and run it:

```bash
# From your laptop — replace <username> with your Scripps username
scp hello-world/hello_hpc.slurm <username>@garibaldi.scripps.edu:~/
```

Then, **on the cluster**:

```bash
sbatch hello_hpc.slurm
```

Slurm prints something like `Submitted batch job 1234567`. Check on it:

```bash
squeue -u $USER                # is it queued / running?
ls -lt hello_hpc_*.out         # output file appears once it runs
cat hello_hpc_*.out            # see the result
```

If you see your hostname and a greeting in the output file, **everything
works end-to-end**. Congratulations — you've just run your first HPC job.

---

## 5. Use the Claude skill

The `scripps-garibaldi-hpc` skill is installed in this repo at
[.claude/skills/scripps-garibaldi-hpc/SKILL.md](.claude/skills/scripps-garibaldi-hpc/SKILL.md).
Claude Code loads it automatically when your question is about
Garibaldi — you don't have to type anything special.

Just ask normally, in plain English. Examples:

> "Write me a Slurm script for a GPU job that runs `train.py` for up
> to 12 hours on 4 CPUs and one A100."

> "I want an interactive session with 32 GB of RAM for 2 hours."

> "My job is stuck in queue — how do I check why?"

> "Translate this PBS script to Slurm for Garibaldi."

Claude will use the cluster-specific defaults (partition names, login
hosts, module workflow) from the skill rather than inventing generic
Slurm advice.

> **Tip for new coders:** if Claude gives you a script and you're not
> sure what a line does, just ask. "What does `#SBATCH --mem=16G` mean?"
> is a totally fine follow-up.

---

## 6. Day-to-day workflow

A typical hackathon loop looks like:

1. Edit code on your laptop (or directly on the cluster with `vim` /
   `nano` / VS Code Remote SSH).
2. If editing locally, sync to the cluster: `scp -r ./code/ <username>@garibaldi.scripps.edu:~/myproject/`
3. Ask Claude to write or update your `sbatch` script.
4. Submit: `sbatch myjob.slurm`
5. Watch: `squeue -u $USER`
6. Inspect logs when it finishes: `cat myjob_*.out`

---

## Troubleshooting

**`Permission denied (publickey,password,...)` during SSH**
Your password or username may be wrong, or your account may not be
provisioned yet. Email `hpc@scripps.edu` to confirm.

**`Connection timed out` during SSH**
You're probably off-campus without VPN. Connect to the Scripps VPN and
try again.

**Job stays in `PD` (pending) for a long time**
The partition is busy or your resource request is too large. Run
`squeue -u $USER --start` to see when Slurm expects to start it, and
consider lowering memory / CPU / GPU asks.

**Job fails immediately with no useful output**
Check both the `.out` and `.err` files. Common culprits: a module you
forgot to `module load`, a typo in a path, or a script that wasn't
marked executable.

**You see `Disk quota exceeded`**
You're over your home-directory quota. Move large files to scratch or a
group directory — ask `hpc@scripps.edu` where you should be writing
big outputs.

**Anything else weird**
Run these three diagnostics and share the output with Claude or with
`hpc@scripps.edu`:

```bash
squeue -u $USER
scontrol show job <jobid>
sinfo
```
