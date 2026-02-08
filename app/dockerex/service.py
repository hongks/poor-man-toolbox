import docker
import humanize
import time

from click import Context

from . import logger
from .config import Config


class DockerEx:
    def __init__(self, configs: Config, context: Context):
        self.configs = configs
        self.context = context

        self.docker = docker.APIClient(base_url="unix://var/run/docker.sock")

    def get_containers(self):
        containers = self.docker.containers(all=True, size=True)
        containers = sorted(
            containers,
            key=lambda container: container["Names"],
            reverse=False,
        )
        # logger.debug(json.dumps(containers[-1], indent=2))

        headers = [
            {"name": "container", "width": 15, "key": lambda c: c["Names"][0][1:]},
            {
                "name": "size",
                "width": 7,
                "key": lambda c: f"{round(c['SizeRootFs'] / 1048576)} MB",
            },
            {"name": "state", "width": 7, "key": lambda c: c["State"]},
            {"name": "status", "width": 25, "key": lambda c: c["Status"]},
        ]

        logger.info(f"results:{self.make_table(headers, containers)}")
        return containers

    def get_info(self, container) -> dict:
        try:
            info = {
                "id": container.id[:12],
                "name": container.name,
                "status": container.status,
                "image": container.image.tags or container.image.short_id,
                "networks": list(container.attrs["NetworkSettings"]["Networks"].keys()),
                "mounts": [],
                "volumes": [],
            }
            # Volumes and mounts
            for mount in container.attrs["Mounts"]:
                mount_info = {
                    "type": mount.get("Type"),
                    "name": mount.get("Name"),
                    "source": mount.get("Source"),
                    "destination": mount.get("Destination"),
                }
                info["mounts"].append(mount_info)
                if mount.get("Name"):
                    info["volumes"].append(mount["Name"])
            # Live stats (CPU %, Memory, Network IO)
            stats = container.stats(stream=False)
            mem_usage = stats["memory_stats"]["usage"]
            mem_limit = stats["memory_stats"].get("limit", 1)
            cpu_delta = (
                stats["cpu_stats"]["cpu_usage"]["total_usage"]
                - stats["precpu_stats"]["cpu_usage"]["total_usage"]
            )
            sys_delta = (
                stats["cpu_stats"]["system_cpu_usage"]
                - stats["precpu_stats"]["system_cpu_usage"]
            )
            cpu_percent = (
                (
                    cpu_delta
                    / sys_delta
                    * len(stats["cpu_stats"]["cpu_usage"]["percpu_usage"])
                )
                * 100.0
                if sys_delta > 0
                else 0
            )
            info["metrics"] = {
                "cpu_percent": round(cpu_percent, 2),
                "memory_usage": humanize.naturalsize(mem_usage),
                "memory_limit": humanize.naturalsize(mem_limit),
                "network_rx": humanize.naturalsize(
                    sum(v["rx_bytes"] for v in stats.get("networks", {}).values())
                ),
                "network_tx": humanize.naturalsize(
                    sum(v["tx_bytes"] for v in stats.get("networks", {}).values())
                ),
            }
            # Volume size (from docker system df)
            df = docker.df()
            volume_sizes = {
                v["Name"]: v["UsageData"]["Size"]
                for v in df["Volumes"]
                if "UsageData" in v
            }
            info["volume_sizes"] = {
                vol: humanize.naturalsize(volume_sizes.get(vol, 0))
                for vol in info["volumes"]
            }
            return info
        except Exception as e:
            return {"error": str(e), "id": container.id[:12], "name": container.name}

    def make_table(self, headers: list[dict], data: list[dict]) -> str:
        table = "\n\n"
        table += "  ".join(f"{h['name']:<{h['width']}}" for h in headers) + "\n"
        table += "  ".join("-" * h["width"] for h in headers) + "\n"

        for row in data:
            line = "  ".join(f"{str(h['key'](row)):<{h['width']}}" for h in headers)
            table += line + "\n"

        return table

    def run(self, target, list):
        # logger.debug(self.configs.projects)

        if list:
            logger.info("retrieving available projects ...")
            tic = time.time()

            for project in self.configs.projects:
                logger.info(f"- {project.name}")

            logger.info(f"... done, retrieved in {time.time() - tic:.3f}s!")
            return

        if target:
            project = next((p for p in self.configs.projects if p.name == target), None)
            if project:
                logger.info(f"project selected: {project.name}.")
                self.get_containers()

            else:
                logger.warning(f"no project found with name: {target}")


# def container_info(name_or_id: str = None):
#
#     results = []
#     if name_or_id:
#         container = client.containers.get(name_or_id)
#         results.append(get_info(container))
#     else:
#         for c in client.containers.list(
#             all=True
#         ):  # all=True includes stopped containers
#             results.append(get_info(c))
#
#     return results
#
#
# if __name__ == "__main__":
#     # Example usage: get all if no ID given
#     details = container_info()
#     logger.info(json.dumps(details, indent=2))
#
