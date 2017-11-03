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

```
git clone https://github.com/kecorbin/argus
cd argus
docker build -t argus .
docker run -ti -e APIC_LOGIN=admin -e APIC_URL=http://myapic -e APIC_PASSWORD=supersecret argus python monitor.py

```


