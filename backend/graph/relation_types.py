# AI Memory OS - Knowledge Graph Relation Types
# Blueprint Section 16: person, project, concept, time, causal

RELATION_TYPES = {
    "same_topic": {"label": "Same Topic", "auto": True},
    "depends_on": {"label": "Depends On", "auto": False},
    "causes": {"label": "Causes", "auto": False},
    "part_of": {"label": "Part Of", "auto": False},
    "related_to": {"label": "Related To", "auto": False},
    "created_by": {"label": "Created By", "auto": False},
    "references": {"label": "References", "auto": False},
    "supersedes": {"label": "Supersedes", "auto": False},
}
