"""
perf_checker.py — Verify network performance setup for Project 11.18
Usage: python perf_checker.py --instance-a i-xxx --instance-b i-yyy [--profile p]
"""
import argparse
import boto3


def check(instance_a: str, instance_b: str, session: boto3.Session) -> None:
    ec2 = session.client("ec2")

    print(f"\n{'='*65}\n  Network Performance Checker — Project 11.18\n{'='*65}\n")

    for label, iid in [("EC2-A", instance_a), ("EC2-B", instance_b)]:
        try:
            resp = ec2.describe_instances(InstanceIds=[iid])
            inst = resp["Reservations"][0]["Instances"][0]

            ena     = inst.get("EnaSupport", False)
            itype   = inst["InstanceType"]
            pg      = inst["Placement"].get("GroupName", "none")
            az      = inst["Placement"]["AvailabilityZone"]
            state   = inst["State"]["Name"]

            print(f"  {label}: {iid}")
            print(f"    State:           {state}")
            print(f"    Instance type:   {itype}")
            print(f"    ENA support:     {'✅ enabled' if ena else '❌ disabled'}")
            print(f"    Placement group: {'✅ ' + pg if pg != 'none' else '⚠️  none (no placement group)'}")
            print(f"    AZ:              {az}")

            # Check network performance from instance type
            high_perf = any(x in itype for x in ["c5n", "m5n", "r5n", "p3dn", "inf"])
            print(f"    Network-optimized type: {'✅ yes' if high_perf else 'ℹ️  standard'}")
            print()

        except Exception as e:
            print(f"  ❌  {label} ({iid}): {e}\n")

    # Check placement group details
    try:
        pgs = ec2.describe_placement_groups(
            Filters=[{"Name": "instance-id", "Values": [instance_a]}]
        )["PlacementGroups"]
        if pgs:
            pg = pgs[0]
            icon = "✅" if pg["State"] == "available" else "⚠️ "
            print(f"  {icon}  Placement Group: {pg['GroupName']}  "
                  f"Strategy={pg['Strategy']}  State={pg['State']}")
        else:
            print("  ℹ️   No placement group found for EC2-A")
    except Exception:
        pass

    print(f"\n  Manual checks to run on EC2:")
    print(f"    ethtool -i eth0          → confirm driver: ena")
    print(f"    ip link show eth0        → confirm mtu 9001")
    print(f"    iperf3 -s                → start server on EC2-A")
    print(f"    iperf3 -c <EC2-A-IP> -P 8 -t 30  → run on EC2-B")

    print(f"\n{'='*65}\n")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--instance-a", required=True)
    p.add_argument("--instance-b", required=True)
    p.add_argument("--profile",    default=None)
    args = p.parse_args()
    check(args.instance_a, args.instance_b, boto3.Session(profile_name=args.profile))


if __name__ == "__main__":
    main()
