# Security Policy

## Supported Versions

We release patches for security vulnerabilities in the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 1.x.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

We take the security of SCUM Server Manager seriously. If you believe you have found a security vulnerability, please report it to us as described below.

### Please Do Not
- Open a public GitHub issue for security vulnerabilities
- Discuss the vulnerability in public forums or social media

### Please Do
1. **Email** the details to: [YOUR_EMAIL@example.com] (replace with your actual email)
2. **Include** the following information:
   - Type of vulnerability
   - Steps to reproduce
   - Potential impact
   - Any possible mitigations
   - Your contact information (optional)

### What to Expect
- **Acknowledgment**: Within 48 hours
- **Initial Assessment**: Within 7 days
- **Status Updates**: Every 7 days until resolved
- **Fix Timeline**: Depends on severity
  - Critical: 1-7 days
  - High: 7-30 days
  - Medium: 30-90 days
  - Low: Next scheduled release

### Security Measures

This project implements the following security measures:

1. **Input Validation**
   - All user inputs are validated
   - SQL injection prevention through parameterized queries
   - Path traversal prevention

2. **RCON Security**
   - Encrypted password storage
   - Secure connection handling
   - Timeout mechanisms

3. **File Operations**
   - Backup creation before modifications
   - Atomic file operations where possible
   - Permission checks

4. **Dependencies**
   - Regular dependency updates
   - Security audit of third-party packages
   - Minimal dependency footprint

### Vulnerability Disclosure

Once a vulnerability is fixed:
1. We will credit the reporter (unless they wish to remain anonymous)
2. Release notes will include security fixes
3. A security advisory may be published for critical issues

### Safe Harbor

We support safe harbor for security researchers who:
- Make a good faith effort to avoid privacy violations and disruption
- Only interact with accounts they own or with explicit permission
- Do not exploit a security issue beyond the minimum necessary to demonstrate it
- Report vulnerabilities promptly
- Keep information about any vulnerabilities confidential until fixed

## Best Practices for Users

To keep your installation secure:

1. **Keep Updated**
   - Always use the latest version
   - Monitor release notes for security updates

2. **Secure Configuration**
   - Use strong RCON passwords
   - Limit RCON access to trusted networks
   - Regularly backup your configuration

3. **Network Security**
   - Use firewalls appropriately
   - Don't expose RCON ports publicly
   - Use VPN for remote management

4. **System Security**
   - Keep your OS and Python updated
   - Use antivirus software
   - Monitor system logs

## Contact

For security-related questions or concerns, please contact:
- **Email**: [YOUR_EMAIL@example.com]
- **PGP Key**: [If available]

---

**Note**: This security policy is subject to change. Please check back regularly for updates.

Last Updated: November 2025
