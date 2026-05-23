"""
alb_checker.py — Verify ALB setup for Project 11.6
Usage: python alb_checker.py --alb-name alb-11-6 [--profile my-profile]
"""
import argparse
import boto3


def check(alb_name: str, session: boto3.Session) -> None:
    elb = session.client("elbv2")
    print(f"\n{'='*60}\n  ALB Checker — Project 11.6  ALB={alb_name}\n{'='*60}\n")

    # ALB state
    albs = elb.describe_load_balancers(Names=[alb_name])["LoadBalancers"]
    if not albs:
        print("❌  ALB not found")
        return
    alb = albs[0]
    state = alb["State"]["Code"]
    icon = "✅" if state == "active" else "❌"
    print(f"{icon}  ALB: {alb['LoadBalancerArn'].split('/')[-1]}  State={state}")
    print(f"     DNS: {alb['DNSName']}")
    print(f"     AZs: {[az['ZoneName'] for az in alb['AvailabilityZones']]}")

    # Target groups
    tgs = elb.describe_target_groups(
        LoadBalancerArn=alb["LoadBalancerArn"]
    )["TargetGroups"]
    print(f"\n  Target Groups ({len(tgs)}):")
    for tg in tgs:
        health = elb.describe_target_health(TargetGroupArn=tg["TargetGroupArn"])
        targets = health["TargetHealthDescriptions"]
        healthy = sum(1 for t in targets if t["TargetHealth"]["State"] == "healthy")
        total = len(targets)
        icon = "✅" if healthy == total and total > 0 else "⚠️ "
        print(f"    {icon}  {tg['TargetGroupName']}  Healthy={healthy}/{total}  "
              f"HealthPath={tg['HealthCheckPath']}")
        for t in targets:
            h = t["TargetHealth"]
            ti = "✅" if h["State"] == "healthy" else "❌"
            print(f"         {ti}  {t['Target']['Id']}  {h['State']}")

    print(f"\n{'='*60}\n")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--alb-name", required=True)
    p.add_argument("--profile", default=None)
    args = p.parse_args()
    check(args.alb_name, boto3.Session(profile_name=args.profile))


if __name__ == "__main__":
    main()
