import polars as pl
from robyn import Request, Robyn, jsonify

from config import Configuration

ctx = pl.SQLContext()
config = Configuration(ctx)
output_mode = config.get_output_mode()

app = Robyn(__file__, config.get_robyn_config())


def df_as_output(res: pl.DataFrame):
    if output_mode == "table":
        return res
    elif output_mode == "json":
        return jsonify(res.write_json(row_oriented=True))


@app.get("/refresh")
def refresh(request: Request):
    config.register_datasets()
    return "done"


@app.get("/schema/:name")
async def get_schema(request: Request):
    name = request.path_params["name"]
    return str(ctx.execute(f"SELECT * FROM {name} LIMIT 0").schema)


@app.get("/tables")
async def list_tables(request: Request):
    res = ctx.execute("SHOW TABLES").collect()
    return df_as_output(res)


@app.post("/sql")
async def sql(request: Request):
    res = ctx.execute(str(request.body)).collect()
    return df_as_output(res)


host, port = config.get_host_port()
app.start(host, port=port)
