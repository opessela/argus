# argus

Argus is a proof of concept for demonstrating the programmability capabilities of UCS and ACI


# Scenario

In a standard VMM integration the dynamic VLAN pool must be pre-provisioned on the UCS Fabric
Interconnects. In very dense deployments this can exhaust logical port resources on FI's.  This exhaustion
is artificial if not all VLAN's are actually needed by VM's hosted in the UCS pod.


# Solution

We will monitor the ACI fabric for notification when policy is provisioned on a given leaf/port, glean
the required information from the notification, and then proceed to provision the required last
mile connectivity onto the appropriate UCS resources (FI's, vNICs, Uplinks)


# Usage

The easiest way to get started is using Docker

***System requirements for installation instructions below: GIT, Docker, and Docker-Compose***


Step 1) Clone the argus repository from GitHub.

```
git clone https://github.com/kecorbin/argus
```

Step 2) Change local directory to the argus project directory.

```
cd argus
```

Step 3) Edit the docker-compose.yml file in the argus project directory to configure ACI integration. You will need the APIC address and credentials. Currently there two locations as shown below.

```
  web:
    ...
    ...
    ...
    environment:
      ...
      ...
      APIC_LOGIN: APIC-USERNAME
      APIC_URL: http://APIC-IP-ADDRESS
      APIC_PASSWORD: APIC-PASSWORD
      ...
```

```
  argus:
    ...
    ...
    ...
    environment:
      APIC_LOGIN: APIC-USERNAME
      APIC_URL: http://APIC-IP-ADDRESS
      APIC_PASSWORD: APIC-PASSWORD
      ...
```

Step 4) Edit the config.py file in the argus project directory to configure UCS integration. 

UCSM Credentials:
```
# ucs info credentials
UCSM_LOGIN = 'UCSM-USERNAME'
UCSM_PASSWORD = 'UCSM-PASSWORD'
```
***In the event of multiple UCS Domains, these credentials need to be consistant.***




Step X) Build the argus container environement with Docker-Compose.
docker-compose build

Step X) Bring the argus container environement online with Docker-Compose.
docker-compose up -d



