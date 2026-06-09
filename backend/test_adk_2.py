from google.adk import Workflow
from google.adk.workflow import START, node

@node
def a(ctx, node_input): print("a"); return "a"
@node
def b(ctx, node_input): print("b"); return "b"
@node
def c(ctx, node_input): print("c"); return "c"
@node
def d(ctx, node_input): print("d"); return "d"

workflow = Workflow(
    name="test",
    edges=[
        (START, a, b, c, d)
    ]
)
from google.adk.workflow import run_workflow_sync
run_workflow_sync(workflow, initial_state={}, message="test")
