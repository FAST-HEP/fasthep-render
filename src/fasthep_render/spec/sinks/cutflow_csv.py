CUTFLOW_CSV_RENDER_SPEC = {
    "name": "hep.render.cutflow_csv",
    "kind": "sink",
    "version": "1.0",
    "params": {
        "spec": {"type": "mapping", "required": False},
        "out": {"type": "string", "required": False},
    },
    "result": {"kind": "artifact", "format": "csv"},
}
