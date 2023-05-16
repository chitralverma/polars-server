import argparse

import polars as pl
import yaml
from robyn.argument_parser import Config as Robyn_Config


class Configuration(object):
    def __init__(self, ctx: pl.SQLContext) -> None:
        self.sql_ctx = ctx

        self.init_config()
        self.register_datasets()

    def init_config(self):
        parser = argparse.ArgumentParser("polars-server")
        parser.add_argument(
            "-c",
            "--config",
            type=argparse.FileType("r"),
            required=True,
            help="Location of config file.",
        )

        parser.add_argument(
            "--dev",
            action="store_true",
            default=False,
            help="Development mode. It restarts the server based on file changes.",
        )

        args = parser.parse_args()
        config_file = args.config
        config = yaml.load(config_file, Loader=yaml.FullLoader)
        assert config.get("polars-server") is not None

        self.config_file = config_file
        self.config = config

    def register_datasets(self):
        for d in self.get_datasets():
            tpe = str(d["type"]).strip().lower()
            path = str(d["path"])
            options = d.get("options")

            if options is None:
                options = {}

            supported_types = ["parquet", "delta", "csv", "ndjson", "ipc"]

            if tpe == "parquet":
                frame = pl.scan_parquet(path, **options)
            elif tpe == "delta":
                frame = pl.scan_delta(path, **options)
            elif tpe == "csv":
                frame = pl.scan_csv(path, **options)
            elif tpe == "ndjson":
                frame = pl.scan_ndjson(path, **options)
            elif tpe == "ipc":
                frame = pl.scan_ipc(path, **options)
            else:
                raise ValueError(
                    f"Type of dataset must be one of {supported_types}, got {tpe}"
                )

            self.sql_ctx.register(name=d["name"], frame=frame)

    def show(self, pretty: bool = True):
        if pretty:
            print(yaml.dump(self.config, indent=2))
        else:
            print(self.get_config())

    def get_config(self):
        return self.config["polars-server"]

    def get_datasets(self):
        return (self.get_config())["datasets"]

    def get_output_mode(self):
        output_mode = self.get_config().get("output-mode")

        if output_mode is None:
            output_mode = "table"
        else:
            output_mode = str(output_mode).lower().strip()

        assert output_mode in ["table", "json"]
        return output_mode

    def get_robyn_config(self):
        api = self.get_config()["api"]
        robyn_config = Robyn_Config()

        workers = api.get("workers")
        processes = api.get("processes")
        log_level = api.get("log-level")

        log_level = "INFO" if log_level is None else str(log_level).upper().strip()
        if log_level not in ["WARN", "DEBUG", "INFO", "ERROR"]:
            log_level = "INFO"

        assert workers is not None and processes is not None

        workers = int(workers)
        processes = int(processes)
        assert workers > 0 and processes > 0

        robyn_config.workers = workers
        robyn_config.processes = processes
        robyn_config.log_level = log_level

        return robyn_config

    def get_host_port(self):
        api = self.get_config()["api"]
        host = api.get("host")
        port = api.get("port")

        assert host is not None and port is not None and int(port) > 0

        host = str(host).strip()

        if host == "localhost":
            host = "127.0.0.1"

        return (host, int(port))
