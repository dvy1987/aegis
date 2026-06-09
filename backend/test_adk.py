from google.adk import Workflow
from google.adk.workflow import START, node

@node
def a(ctx, node_input): return "a"
@node
def b(ctx, node_input): return "b"

workflow = Workflow(
    name="test",
    edges=[
        (START, a, b)
    ]
)
print("Workflow initialized successfully")
