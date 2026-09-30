# Dependency model lives in blocker.py (kept together since they're created
# in the same transactions by causal_graph.py). This file re-exports it so
# `from app.models import dependency` also works, per the file layout in
# section 43 of the spec.
from app.models.blocker import Dependency  # noqa: F401
