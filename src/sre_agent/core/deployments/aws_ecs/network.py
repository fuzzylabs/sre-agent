"""VPC and subnet management for ECS."""

from collections.abc import Callable
from typing import Any

from boto3.session import Session

from sre_agent.core.deployments.aws_ecs.models import NetworkSelection


def create_basic_vpc(
    session: Session,
    project_name: str,
    reporter: Callable[[str], None],
) -> NetworkSelection:
    """Create a simple VPC with one public and one private subnet."""
    ec2 = session.client("ec2")

    reporter("Creating VPC (private networking foundation)")
    vpc_id = ec2.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]["VpcId"]
    ec2.modify_vpc_attribute(VpcId=vpc_id, EnableDnsSupport={"Value": True})
    ec2.modify_vpc_attribute(VpcId=vpc_id, EnableDnsHostnames={"Value": True})
    _tag_resource(ec2, vpc_id, f"{project_name}-vpc")

    reporter("Creating internet gateway (public subnet access)")
    igw_id = ec2.create_internet_gateway()["InternetGateway"]["InternetGatewayId"]
    ec2.attach_internet_gateway(InternetGatewayId=igw_id, VpcId=vpc_id)
    _tag_resource(ec2, igw_id, f"{project_name}-igw")

    availability_zone = _first_availability_zone(ec2)

    reporter("Creating public subnet (used by NAT gateway)")
    public_subnet_id = ec2.create_subnet(
        VpcId=vpc_id,
        CidrBlock="10.0.0.0/24",
        AvailabilityZone=availability_zone,
    )["Subnet"]["SubnetId"]
    ec2.modify_subnet_attribute(
        SubnetId=public_subnet_id,
        MapPublicIpOnLaunch={"Value": True},
    )
    _tag_resource(ec2, public_subnet_id, f"{project_name}-public")

    reporter("Creating private subnet (where ECS tasks will run)")
    private_subnet_id = ec2.create_subnet(
        VpcId=vpc_id,
        CidrBlock="10.0.1.0/24",
        AvailabilityZone=availability_zone,
    )["Subnet"]["SubnetId"]
    ec2.modify_subnet_attribute(
        SubnetId=private_subnet_id,
        MapPublicIpOnLaunch={"Value": False},
    )
    _tag_resource(ec2, private_subnet_id, f"{project_name}-private")

    reporter("Creating routes for public subnet")
    public_route_table_id = ec2.create_route_table(VpcId=vpc_id)["RouteTable"]["RouteTableId"]
    ec2.create_route(
        RouteTableId=public_route_table_id,
        DestinationCidrBlock="0.0.0.0/0",
        GatewayId=igw_id,
    )
    ec2.associate_route_table(RouteTableId=public_route_table_id, SubnetId=public_subnet_id)
    _tag_resource(ec2, public_route_table_id, f"{project_name}-public-rt")

    reporter("Creating NAT gateway for outbound access (this can take a few minutes)")
    allocation_id = ec2.allocate_address(Domain="vpc")["AllocationId"]
    nat_gateway_id = ec2.create_nat_gateway(
        SubnetId=public_subnet_id,
        AllocationId=allocation_id,
    )["NatGateway"]["NatGatewayId"]
    ec2.get_waiter("nat_gateway_available").wait(NatGatewayIds=[nat_gateway_id])

    reporter("Creating routes for private subnet")
    private_route_table_id = ec2.create_route_table(VpcId=vpc_id)["RouteTable"]["RouteTableId"]
    ec2.create_route(
        RouteTableId=private_route_table_id,
        DestinationCidrBlock="0.0.0.0/0",
        NatGatewayId=nat_gateway_id,
    )
    ec2.associate_route_table(RouteTableId=private_route_table_id, SubnetId=private_subnet_id)
    _tag_resource(ec2, private_route_table_id, f"{project_name}-private-rt")

    reporter("VPC created successfully")
    return NetworkSelection(vpc_id=vpc_id, private_subnet_ids=[private_subnet_id])


def _tag_resource(ec2: Any, resource_id: str, name: str) -> None:
    """Apply a Name tag to a resource."""
    ec2.create_tags(Resources=[resource_id], Tags=[{"Key": "Name", "Value": name}])


def _first_availability_zone(ec2: Any) -> str:
    """Fetch the first availability zone."""
    response = ec2.describe_availability_zones()
    zones = response.get("AvailabilityZones", [])
    if not zones:
        raise RuntimeError("No availability zones found for this region.")
    return str(zones[0]["ZoneName"])
