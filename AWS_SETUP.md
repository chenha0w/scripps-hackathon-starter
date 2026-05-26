# AWS Setup for the Scripps Research 2026 Hackathon

End-to-end instructions for configuring your computer to use the
`/hackathon-aws` Claude skill against the Scripps Research Hackathon AWS
account.

By the end of this guide you'll be able to:

- Run `aws` commands against account `127696279288` in `us-west-2`
- Have Claude execute those commands on your behalf via the skill
- Run `./test_skill.sh` to verify everything works

---

## 1. Install the AWS CLI v2

Pick the section for your OS.

### macOS

Recommended (Homebrew):

```bash
brew install awscli
```

Or the official PKG installer:

```bash
curl "https://awscli.amazonaws.com/AWSCLIV2.pkg" -o /tmp/AWSCLIV2.pkg
sudo installer -pkg /tmp/AWSCLIV2.pkg -target /
```

### Linux (x86_64)

```bash
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o /tmp/awscliv2.zip
unzip /tmp/awscliv2.zip -d /tmp
sudo /tmp/aws/install
```

For ARM64 hosts, replace the zip with `awscli-exe-linux-aarch64.zip`.

### Windows

Download and run the MSI installer:

<https://awscli.amazonaws.com/AWSCLIV2.msi>

After installation, open a **new** PowerShell window so the updated `PATH`
takes effect. The rest of this guide assumes a Unix-like shell — on Windows,
either use WSL (recommended) or translate the shell commands to PowerShell.

### Verify

```bash
aws --version
```

You should see something like `aws-cli/2.x.y …`. If the command isn't found,
open a new terminal so `PATH` is refreshed.

---

## 2. Configure your SSO profile

You'll create a named profile that points at the hackathon's AWS IAM
Identity Center (formerly SSO).

Pick a short profile name — these instructions use `bgood-scripps` as the
example. Substitute your own name throughout (the test script defaults to
`bgood-scripps` and you can edit it at the top of `test_skill.sh`).

### Option A — interactive `aws configure sso`

```bash
aws configure sso
```

Answer the prompts with these values:

| Prompt                  | Value                                                  |
| ----------------------- | ------------------------------------------------------ |
| SSO session name        | `scripps-hackathon`                                    |
| SSO start URL           | `https://d-9267e96a16.awsapps.com/start`               |
| SSO region              | `us-west-2`                                            |
| SSO registration scopes | *(leave default — press Enter — `sso:account:access`)* |

> **Don't leave the session name blank.** A blank name triggers the legacy
> profile format (the CLI prints `WARNING: Configuring using legacy format`),
> which doesn't support token auto-refresh and can't be reused across
> multiple profiles. Always supply a name.

A browser window will open. Sign in with your Scripps SSO credentials
(e.g. `bgood@scripps.edu`) and approve the device authorization.

Back in the terminal, you'll be asked which account and role to use:

| Prompt | Value |
|---|---|
| Account | `Scripps Research Hackathon (127696279288)` |
| Role | the role you've been granted (for this event it's usually `Hackathon`; admins may see `AWSAdministratorAccess`) |
| Default client region | `us-west-2` |
| Default output format | `json` |
| Profile name | `bgood-scripps` *(or your preferred name)* |

### Option B — edit `~/.aws/config` directly

If you prefer to skip the prompts, create or append these two stanzas to
`~/.aws/config` (the modern session-based format):

```ini
[sso-session scripps-hackathon]
sso_start_url = https://d-9267e96a16.awsapps.com/start
sso_region = us-west-2
sso_registration_scopes = sso:account:access

[profile bgood-scripps]
sso_session = scripps-hackathon
sso_account_id = 127696279288
sso_role_name = Hackathon
region = us-west-2
output = json
```

Replace `bgood-scripps` (and the role name, if yours differs — sign in at
<https://d-9267e96a16.awsapps.com/start> to see exactly what role you've
been granted). The
`[sso-session scripps-hackathon]` block can be reused by additional profiles
in the same account — you only need one session block per identity center.

---

## 3. Log in

SSO tokens expire (typically every 8–12 hours). Whenever yours expires,
re-run:

```bash
aws sso login --profile bgood-scripps
```

A browser opens; approve the request and you're done. The token is cached
under `~/.aws/sso/cache/`.

If you ever see `Token has expired and refresh failed`, just run the login
command again.

---

## 4. Verify access

Confirm the CLI can talk to AWS as you:

```bash
aws sts get-caller-identity --profile bgood-scripps
```

You should see JSON containing:

- `"Account": "127696279288"`
- `"Arn": "arn:aws:sts::127696279288:assumed-role/AWSReservedSSO_…/bgood@scripps.edu"`

Quick listing check:

```bash
aws s3 ls --profile bgood-scripps --region us-west-2
aws ec2 describe-instances --profile bgood-scripps --region us-west-2 \
  --query 'Reservations[].Instances[].[InstanceId,State.Name,Tags]'
```

---

## 5. Run the end-to-end smoke test

From the repo root:

```bash
./test_skill.sh
```

This walks through each capability the skill exposes: SSO login check,
create a personal S3 bucket, write/read a `hello-world.txt`, read from an
Amazon Open Data bucket, launch a `t3.micro`, wait for `running`, then
terminate. Every step prints PASS/FAIL and the script exits non-zero if
anything failed.

Flags:

- `--no-ec2` — S3-only (skip the instance launch)
- `--keep-bucket` — don't delete the test object at the end

If you used a profile name other than `bgood-scripps`, edit the `PROFILE`
variable at the top of `test_skill.sh` before running.

---

## 6. Use the Claude skill

Install the slash command (one-time):

```bash
# Per-project
cp .claude/commands/hackathon-aws.md <your-project>/.claude/commands/

# Or globally for all projects
cp .claude/commands/hackathon-aws.md ~/.claude/commands/
```

Then in any Claude Code session:

```
/hackathon-aws Launch a t3.medium, copy my analysis script to it, and run it
```

Two things to keep in mind:

1. **Tell Claude your profile name once per session** if it isn't
   `inewman-wsl` (the skill's default placeholder). For example:
   "Use profile `bgood-scripps` for all AWS commands."
2. **Re-login when prompted.** If Claude reports `Token has expired`, run
   `aws sso login --profile bgood-scripps` in your terminal and tell Claude
   to retry.

---

## Troubleshooting

**`aws: command not found`**
Open a new terminal. If still missing, verify the install location is on
your `PATH` (`which aws` on macOS/Linux, `where aws` on Windows).

**`Unable to locate credentials` / `The SSO session associated with this profile has expired`**
Run `aws sso login --profile <your-profile>`.

**Browser doesn't open during `aws sso login`**
The CLI prints a URL and a code. Open the URL in any browser, enter the
code, and complete sign-in. The CLI will continue once it sees the
approval.

**`AccessDenied` on a specific action**
Your SSO role may not include that permission. Check with the hackathon
admin — different participants may have been granted different roles.

**Bucket name already taken**
S3 bucket names are globally unique. Add a suffix to the `BUCKET` variable
in `test_skill.sh` (e.g. `scrippsresearch-bgood-hackathon-2026`).
