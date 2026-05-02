
# 1. Overview (what this does)

This guide connects a Windows machine to a Linux machine using **Tailscale** (a zero-config private VPN) and **SSH**. No router port-forwarding is required and it works even behind institutional NAT/firewalls.

Example from your setup:

* Linux username: `ev`
* Linux Tailscale IP: `100.97.228.4`
* Windows Tailscale IP: `100.90.56.107`

# 2. Prerequisites

* Admin rights on both machines (or ability to `sudo` on Linux and install on Windows).
* Internet access to sign into Tailscale.
* A Tailscale account (use the same email on all devices).

# 3. Install Tailscale

## On Linux (Ubuntu/Debian)

```bash
# install tailscale
curl -fsSL https://tailscale.com/install.sh | sh

# start / login
sudo tailscale up
# follow the printed URL in a browser and sign in with your Tailscale account
```

## On Windows

* Download and run the Windows installer from [https://tailscale.com/download/windows](https://tailscale.com/download/windows)
* Sign in using the *same* Tailscale account you used on Linux.

# 4. Verify Tailscale connectivity

### On Linux:

```bash
# list devices and get the device's Tailscale IP
sudo tailscale status
tailscale ip
```

Expected example output (shows both Windows & Linux):

```
100.97.228.4  ev-desktop  eviitjammu@  linux
100.90.56.107 nagesh      eviitjammu@  windows
```

### On Windows (PowerShell)

If CLI is not on your PATH use the full path:

```powershell
& "C:\Program Files\Tailscale\tailscale.exe" status
& "C:\Program Files\Tailscale\tailscale.exe" ip
```

# 5. Install and enable SSH on Linux

```bash
# install ssh server (if not already)
sudo apt update
sudo apt install openssh-server

# enable and start ssh
sudo systemctl enable --now ssh

# verify
sudo systemctl status ssh
sudo ss -tlnp | grep sshd
```

You should see SSH listening on `0.0.0.0:22` and `[::]:22`.

# 6. Test connectivity over Tailscale

From Windows PowerShell:

```powershell
ping 100.97.228.4
Test-NetConnection -ComputerName 100.97.228.4 -Port 22
ssh ev@100.97.228.4
```

If `ssh` times out, re-check that both devices are logged into the same Tailscale account and that `tailscale status` shows both devices.

# 7. (Recommended) Set up SSH key authentication (better than passwords)

### On Windows (generate key)

PowerShell (or use WSL/Git Bash):

```powershell
ssh-keygen -t ed25519 -f $env:USERPROFILE\.ssh\id_ed25519
# (press Enter for defaults, optionally set a passphrase)
```

### Copy the public key to Linux

From Windows (replace IP and username if needed):

```powershell
type $env:USERPROFILE\.ssh\id_ed25519.pub | ssh ev@100.97.228.4 "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 700 ~/.ssh && chmod 600 ~/.ssh/authorized_keys"
```

Or use `ssh-copy-id` from a Linux/WSL shell:

```bash
ssh-copy-id -i ~/.ssh/id_ed25519.pub ev@100.97.228.4
```

### Test key login from Windows:

```powershell
ssh ev@100.97.228.4
# It should not ask for the user password if keys are set correctly (unless you set a key-passphrase)
```

# 8. (Optional Security Hardening)

* Disable password authentication (once key auth verified):
  Edit `/etc/ssh/sshd_config` on Linux:

  ```
  PasswordAuthentication no
  ChallengeResponseAuthentication no
  PermitRootLogin no
  ```

  Then restart:

  ```bash
  sudo systemctl restart ssh
  ```
* (Optional) Change SSH listening port in `sshd_config` and firewall accordingly.
* Ensure only necessary users have SSH access (use `AllowUsers ev` in `sshd_config`).

# 9. (Optional) Configure UFW (firewall) — if you enable it later

```bash
sudo ufw allow OpenSSH
sudo ufw allow from 100.0.0.0/8    # allow Tailscale private IP range
sudo ufw enable
sudo ufw status
```

# 10. Useful commands for daily remote work

* SSH: `ssh ev@100.97.228.4`
* Copy files from Windows → Linux: from PowerShell

  ```powershell
  scp C:\path\file.txt ev@100.97.228.4:/home/ev/
  ```
* Copy files from Linux → Windows (from Windows PowerShell):

  ```powershell
  scp ev@100.97.228.4:/home/ev/file.txt C:\Users\nages\Downloads\
  ```
* Show active sessions on Linux: `who` / `w`
* Forward a local port via SSH (example: forward local 8080 to remote 3000):

  ```powershell
  ssh -L 8080:localhost:3000 ev@100.97.228.4
  ```

# 11. Troubleshooting checklist

If you can’t connect, check in order:

1. Both devices appear in the same Tailscale tailnet (`tailscale status` on both).
2. `tailscale ip` returns the expected 100.x.x.x addresses.
3. SSH server running on Linux: `sudo systemctl status ssh`.
4. SSH listening on all interfaces: `sudo ss -tlnp | grep sshd` should show `0.0.0.0:22`.
5. Firewall (UFW) is not blocking Tailscale or port 22: `sudo ufw status`.
6. Tailscale "Shields Up" is off: `sudo tailscale debug prefs` → `"ShieldsUp": false`.
7. From Windows: `ping <linux-tailscale-ip>` — a failing ping usually means Tailscale visibility/account mismatch.
8. Ensure both devices use the **same Tailscale account** (most common cause of connectivity failure).

# 12. Alternatives (if you don’t want to use Tailscale)

* **Ngrok** (quick TCP tunnel): `ngrok tcp 22` — useful for temporary access.
* **ZeroTier** — another VPN-like solution.
* Traditional port-forwarding (requires router admin and public IP).

# 13. Extra tips / best practices

* Use **key-based auth** and disable password auth.
* Use a passphrase for your private key and an SSH agent (Windows: `ssh-agent`, or `Pageant` with PuTTY).
* Keep `tailscale` updated.
* Avoid exposing SSH to the open internet — Tailscale is safer.

---

