"""
ecs_checker.py — Verify ECS container networking for Project 11.17
Usage: python ecs_checker.py --cluster cluster-11-17 [--profile my-profile]
"""
import argparse
import boto3


def check(cluster: str, session: boto3.Session) -> None:
    ecs = session.client("ecs")
    sd  = session.client("servicediscovery")

    print(f"\n{'='*65}\n  ECS Checker — Project 11.17  Cluster={cluster}\n{'='*65}\n")

    # 1. Cluster status
    clusters = ecs.describe_clusters(clusters=[cluster])["clusters"]
    if not clusters:
        print(f"❌  Cluster '{cluster}' not found")
        return
    c = clusters[0]
    icon = "✅" if c["status"] == "ACTIVE" else "❌"
    print(f"{icon}  Cluster: {c['clusterName']}  Status={c['status']}")
    print(f"     Active services: {c['activeServicesCount']}")
    print(f"     Running tasks:   {c['runningTasksCount']}")

    # 2. Services
    svc_arns = ecs.list_services(cluster=cluster)["serviceArns"]
    if svc_arns:
        services = ecs.describe_services(cluster=cluster, services=svc_arns)["services"]
        print(f"\n  Services ({len(services)}):")
        for svc in services:
            running  = svc["runningCount"]
            desired  = svc["desiredCount"]
            icon = "✅" if running == desired and desired > 0 else "⚠️ "
            print(f"    {icon}  {svc['serviceName']:25s}  Running={running}/{desired}  Status={svc['status']}")

    # 3. Tasks — check awsvpc mode and VPC IPs
    task_arns = ecs.list_tasks(cluster=cluster)["taskArns"]
    if task_arns:
        tasks = ecs.describe_tasks(cluster=cluster, tasks=task_arns[:5])["tasks"]
        print(f"\n  Tasks (showing up to 5 of {len(task_arns)}):")
        for t in tasks:
            # Find ENI attachment
            eni_details = {}
            for att in t.get("attachments", []):
                if att["type"] == "ElasticNetworkInterface":
                    eni_details = {d["name"]: d["value"] for d in att["details"]}
            private_ip = eni_details.get("privateIPv4Address", "—")
            public_ip  = eni_details.get("publicIPv4Address", "none")
            icon = "✅" if private_ip != "—" else "⚠️ "
            print(f"    {icon}  {t['taskArn'].split('/')[-1][:20]}  "
                  f"PrivateIP={private_ip}  PublicIP={public_ip}  "
                  f"Status={t['lastStatus']}")

    # 4. Cloud Map service discovery
    print(f"\n  Cloud Map Services:")
    try:
        namespaces = sd.list_namespaces()["Namespaces"]
        for ns in namespaces:
            if ns["Type"] == "DNS_PRIVATE":
                services_sd = sd.list_services(
                    Filters=[{"Name": "NAMESPACE_ID", "Values": [ns["Id"]]}]
                )["Services"]
                for svc_sd in services_sd:
                    instances = sd.list_instances(ServiceId=svc_sd["Id"])["Instances"]
                    print(f"    ✅  {svc_sd['Name']}.{ns['Name']}  "
                          f"Instances={len(instances)}")
                    for inst in instances[:3]:
                        ip = inst["Attributes"].get("AWS_INSTANCE_IPV4", "—")
                        print(f"         → {ip}")
    except Exception as e:
        print(f"    ⚠️   Cloud Map check failed: {e}")

    print(f"\n{'='*65}\n")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--cluster", required=True)
    p.add_argument("--profile", default=None)
    args = p.parse_args()
    check(args.cluster, boto3.Session(profile_name=args.profile))


if __name__ == "__main__":
    main()
