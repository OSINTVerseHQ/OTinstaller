# Tool Tagging Reference

This document records the capability, topic, and accepts tags assigned to each tool
in the registry, along with the reasoning. Edit this file to correct tags, then
regenerate the registry.

## Tag Definitions

| Capability | Description |
|------------|-------------|
| username-search | Search for accounts by username across platforms |
| email-search | Search for accounts/info by email address |
| domain-recon | Gather information about a domain |
| ip-recon | Gather information about an IP address |
| phone-search | Search for info by phone number |
| social-media | Extract data from social media platforms |
| breach-search | Check breach databases for credentials |
| metadata-extraction | Extract metadata from files/urls |
| subdomain-enum | Enumerate subdomains of a domain |
| google-recon | Google search/dorking for recon |
| image-recon | Reverse image search / image analysis |
| dual-use | Tool has significant misuse potential for sensitive personal data lookups |
| darkweb | Dark web / Tor / onion service enumeration |
| cloud | Cloud infrastructure enumeration |
| network | Network infrastructure enumeration |
| vulnerability-scan | Vulnerability scanning |
| web-scanner | Web application scanning |

| Accepts Value | Description |
|---------------|-------------|
| username | Social media username / handle |
| email | Email address |
| domain | Domain name (e.g., example.com) |
| ip | IP address |
| phone | Phone number |
| url | URL |
| name | Person's real name |

## Tool Tags

### maigret
- **Capabilities**: username-search
- **Topics**: username
- **Accepts**: username
- **Reasoning**: searches accounts by username

### ghunt
- **Capabilities**: google-recon, email-search, username-search
- **Topics**: google, email, username
- **Accepts**: username, email
- **Reasoning**: searches accounts by username; searches by email/breach data; uses Google search/dorking

### spiderfoot
- **Capabilities**: domain-recon, ip-recon, subdomain-enum, email-search, google-recon, metadata-extraction, username-search
- **Topics**: domain, ip, subdomain, email, google, metadata, username
- **Accepts**: domain, ip, username, email
- **Reasoning**: searches accounts by username; searches by email/breach data; performs domain reconnaissance; enumerates subdomains; performs IP reconnaissance; uses Google search/dorking; extracts metadata; performs IP reconnaissance

### instaloader
- **Capabilities**: social-media, metadata-extraction, username-search
- **Topics**: instagram, social-media, metadata, username
- **Accepts**: username, url
- **Reasoning**: searches accounts by username; extracts social media data; extracts social media data; extracts metadata

### sherlock
- **Capabilities**: username-search, social-media
- **Topics**: username, social-media
- **Accepts**: username
- **Reasoning**: searches accounts by username; extracts social media data; extracts social media data

### holehe
- **Capabilities**: email-search, social-media, username-search
- **Topics**: email, social-media, username
- **Accepts**: email, username
- **Reasoning**: searches accounts by username; searches by email/breach data; extracts social media data; extracts social media data

### bbot
- **Capabilities**: domain-recon, subdomain-enum, ip-recon, google-recon, metadata-extraction, username-search
- **Topics**: domain, subdomain, ip, google, username
- **Accepts**: domain, ip
- **Reasoning**: searches accounts by username; performs domain reconnaissance; enumerates subdomains; performs IP reconnaissance; uses Google search/dorking; extracts metadata; performs IP reconnaissance

### dnstwist
- **Capabilities**: domain-recon, ip-recon
- **Topics**: domain, ip
- **Accepts**: domain, ip
- **Reasoning**: performs domain reconnaissance; performs IP reconnaissance; performs IP reconnaissance

### h8mail
- **Capabilities**: email-search, breach-search, dual-use
- **Topics**: email, breach
- **Accepts**: email
- **Reasoning**: searches by email/breach data; queries breach databases; dual-use: sensitive personal data lookups

### user-scanner
- **Capabilities**: username-search, email-search, metadata-extraction, dual-use
- **Topics**: username, email, metadata
- **Accepts**: username, email
- **Reasoning**: searches accounts by username; searches by email/breach data; extracts metadata; dual-use: sensitive personal data lookups

### torbot
- **Capabilities**: darkweb, google-recon, domain-recon
- **Topics**: darkweb, tor, domain
- **Accepts**: url, domain
- **Reasoning**: performs domain reconnaissance; uses Google search/dorking; darkweb/Tor enumeration

### toutatis
- **Capabilities**: phone-search, social-media, metadata-extraction, dual-use
- **Topics**: phone, social-media, metadata
- **Accepts**: phone
- **Reasoning**: searches by phone number; extracts social media data; extracts social media data; extracts metadata; dual-use: sensitive personal data lookups

### ivre
- **Capabilities**: domain-recon, ip-recon, subdomain-enum, network
- **Topics**: network, domain, ip, subdomain
- **Accepts**: domain, ip
- **Reasoning**: performs domain reconnaissance; enumerates subdomains; performs IP reconnaissance; performs IP reconnaissance; network infrastructure enumeration

### aliens-eye
- **Capabilities**: username-search, social-media, ai
- **Topics**: username, social-media, ai
- **Accepts**: username
- **Reasoning**: searches accounts by username; extracts social media data; extracts social media data

### paramspider
- **Capabilities**: google-recon, metadata-extraction, domain-recon
- **Topics**: google, metadata, url, domain
- **Accepts**: domain, url
- **Reasoning**: performs domain reconnaissance; uses Google search/dorking; extracts metadata

### nexfil
- **Capabilities**: username-search, social-media
- **Topics**: username, social-media
- **Accepts**: username
- **Reasoning**: searches accounts by username; extracts social media data; extracts social media data

### yark
- **Capabilities**: social-media, google-recon, username-search
- **Topics**: youtube, social-media, google, username
- **Accepts**: url, username, name
- **Reasoning**: searches accounts by username; extracts social media data; extracts social media data; uses Google search/dorking

### cloud-enum
- **Capabilities**: domain-recon, ip-recon, subdomain-enum, cloud
- **Topics**: cloud, domain, ip, subdomain
- **Accepts**: domain, ip
- **Reasoning**: performs domain reconnaissance; enumerates subdomains; performs IP reconnaissance; performs IP reconnaissance; cloud infrastructure enumeration

### ignorant
- **Capabilities**: phone-search, social-media, dual-use
- **Topics**: phone, social-media
- **Accepts**: phone
- **Reasoning**: searches by phone number; extracts social media data; extracts social media data; dual-use: sensitive personal data lookups

### socialscan
- **Capabilities**: username-search, email-search
- **Topics**: username, email
- **Accepts**: username, email
- **Reasoning**: searches accounts by username; searches by email/breach data

### fsociety
- **Capabilities**: domain-recon, subdomain-enum, username-search, email-search, breach-search, dual-use
- **Topics**: domain, subdomain, username, email, breach
- **Accepts**: domain, username, email
- **Reasoning**: searches accounts by username; searches by email/breach data; performs domain reconnaissance; enumerates subdomains; queries breach databases; dual-use: sensitive personal data lookups

### blackwidow
- **Capabilities**: domain-recon, subdomain-enum, vulnerability-scan, web-scanner
- **Topics**: web, domain, subdomain, vulnerability
- **Accepts**: url, domain
- **Reasoning**: performs domain reconnaissance; enumerates subdomains; performs vulnerability scanning; scans web applications

### onionsearch
- **Capabilities**: darkweb, google-recon
- **Topics**: darkweb, tor, onion
- **Accepts**: url
- **Reasoning**: uses Google search/dorking; darkweb/Tor enumeration

### openosint
- **Capabilities**: username-search, email-search, domain-recon, social-media, google-recon, ai
- **Topics**: username, email, domain, social-media, google, ai
- **Accepts**: username, email, domain
- **Reasoning**: searches accounts by username; searches by email/breach data; performs domain reconnaissance; extracts social media data; extracts social media data; uses Google search/dorking

### crosslinked
- **Capabilities**: social-media, metadata-extraction, google-recon, username-search, email-search
- **Topics**: linkedin, social-media, metadata, google, username, email
- **Accepts**: username, email, name
- **Reasoning**: searches accounts by username; searches by email/breach data; extracts social media data; extracts social media data; uses Google search/dorking; extracts metadata

### whatsapp-osint
- **Capabilities**: social-media, phone-search, dual-use
- **Topics**: whatsapp, social-media, phone
- **Accepts**: phone, name
- **Reasoning**: searches by phone number; extracts social media data; extracts social media data; dual-use: sensitive personal data lookups

### instagram-monitor
- **Capabilities**: social-media, username-search, dual-use
- **Topics**: instagram, social-media, username
- **Accepts**: username
- **Reasoning**: searches accounts by username; extracts social media data; extracts social media data; dual-use: sensitive personal data lookups

### mailaccess
- **Capabilities**: email-search, breach-search, dual-use
- **Topics**: email, breach
- **Accepts**: email
- **Reasoning**: searches by email/breach data; queries breach databases; dual-use: sensitive personal data lookups

### secator
- **Capabilities**: domain-recon, subdomain-enum, ip-recon, username-search, email-search, breach-search, google-recon, dual-use
- **Topics**: domain, subdomain, ip, username, email, breach, recon
- **Accepts**: domain, ip, username, email
- **Reasoning**: searches accounts by username; searches by email/breach data; performs domain reconnaissance; enumerates subdomains; performs IP reconnaissance; queries breach databases; uses Google search/dorking; performs IP reconnaissance; dual-use: sensitive personal data lookups

### socid-extractor
- **Capabilities**: metadata-extraction, username-search, social-media
- **Topics**: metadata, username, social-media, profile
- **Accepts**: url, username
- **Reasoning**: searches accounts by username; extracts social media data; extracts social media data; extracts metadata

### dnsgen
- **Capabilities**: domain-recon, subdomain-enum
- **Topics**: domain, subdomain
- **Accepts**: domain
- **Reasoning**: performs domain reconnaissance; enumerates subdomains

### sitedorks
- **Capabilities**: google-recon, metadata-extraction
- **Topics**: google, dork, metadata
- **Accepts**: domain, url
- **Reasoning**: uses Google search/dorking; extracts metadata

### linkook
- **Capabilities**: username-search, email-search, social-media
- **Topics**: username, email, social-media
- **Accepts**: username, email
- **Reasoning**: searches accounts by username; searches by email/breach data; extracts social media data; extracts social media data

### osint-brazuca-regex
- **Capabilities**: google-recon, metadata-extraction
- **Topics**: brazil, regex, google, metadata
- **Accepts**: domain, name
- **Reasoning**: uses Google search/dorking; extracts metadata

### finalrecon
- **Capabilities**: domain-recon, subdomain-enum, ip-recon, google-recon, metadata-extraction
- **Topics**: domain, subdomain, ip, google, metadata
- **Accepts**: domain, ip
- **Reasoning**: performs domain reconnaissance; enumerates subdomains; performs IP reconnaissance; uses Google search/dorking; extracts metadata; performs IP reconnaissance

### fierce
- **Capabilities**: domain-recon, ip-recon, subdomain-enum
- **Topics**: domain, ip, subdomain
- **Accepts**: domain, ip
- **Reasoning**: performs domain reconnaissance; enumerates subdomains; performs IP reconnaissance; performs IP reconnaissance

### pywerview
- **Capabilities**: domain-recon, subdomain-enum, username-search, email-search
- **Topics**: active-directory, domain, username, email
- **Accepts**: domain, username
- **Reasoning**: searches accounts by username; searches by email/breach data; performs domain reconnaissance; enumerates subdomains

### airecon
- **Capabilities**: domain-recon, subdomain-enum, ip-recon, ai, google-recon
- **Topics**: domain, subdomain, ip, ai, google
- **Accepts**: domain, ip
- **Reasoning**: performs domain reconnaissance; enumerates subdomains; performs IP reconnaissance; uses Google search/dorking; performs IP reconnaissance

### opendoor
- **Capabilities**: domain-recon, subdomain-enum, ip-recon, vulnerability-scan, dual-use
- **Topics**: vulnerability, domain, ip, subdomain
- **Accepts**: domain, ip
- **Reasoning**: performs domain reconnaissance; enumerates subdomains; performs IP reconnaissance; performs IP reconnaissance; dual-use: sensitive personal data lookups; performs vulnerability scanning

### ctfr
- **Capabilities**: domain-recon, subdomain-enum
- **Topics**: domain, subdomain, certificate
- **Accepts**: domain
- **Reasoning**: performs domain reconnaissance; enumerates subdomains
