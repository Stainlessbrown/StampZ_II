# StampZ

A image analysis application optimized for philatelic images.

## Compatibility

### Linux Systems

The Linux executable (`StampZ_linux-x64`) is built on Ubuntu 20.04 for maximum compatibility:

- ✅ **Compatible with:** Ubuntu 18.04+, Linux Mint 20+, Debian 10+, CentOS 8+
- ✅ **Tested on:** Linux Mint 22, Ubuntu 20.04, Ubuntu 22.04, Ubuntu 24.04
- ⚠️ **Note:** For Ubuntu 18.04.6 users experiencing GLIBC errors, see [LINUX_MINT_22_FIX.md](LINUX_MINT_22_FIX.md) for troubleshooting steps

### Other Platforms

- **Windows:** Windows 10/11 (x64)
- **macOS:** macOS 11+ (Intel and Apple Silicon)

## Installation

1. Download the appropriate executable for your platform from the [Releases](https://github.com/Stainlessbrown/StampZ/releases) page
2. On Linux/macOS: Make the file executable with `chmod +x StampZ_*`
3. Run the application

### Running from Source

If the executable doesn't work on your system, you can run from source:

```bash
git clone https://github.com/Stainlessbrown/StampZ.git
cd StampZ
pip install -r requirements.txt
python3 main.py
```

## Support

For issues with specific Linux distributions, check the troubleshooting guides:
- [Linux Mint 22 Issues](LINUX_MINT_22_FIX.md)
