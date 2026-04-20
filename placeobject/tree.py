from __future__ import annotations

import py_trees

from .actions import LowerObject, MoveToPlace, ReleaseObject

PLACE_SEQUENCE = ["MoveToPlace", 
                  "LowerObject", 
                  "ReleaseObject"]


def make_place_object_tree(controller) -> py_trees.behaviour.Behaviour:
    """Build and return the root of the PlaceObject behaviour tree.

    Structure::

        PlaceObject Sequence {→}
          ├── MoveToPlace      pre: ObjectSecuredInGripper, PlaceLocationVisible
          │                    post: AtPlaceLocation
          ├── LowerObject      pre: AtPlaceLocation
          │                    post: ObjectAtPlaceHeight
          └── ReleaseObject    pre: ObjectAtPlaceHeight
                               post: PlacementConfirmed → sets place_succeeded=True
    """
    root = py_trees.composites.Sequence("PlaceObject", memory=True)
    root.add_children([
        MoveToPlace("MoveToPlace", controller),
        LowerObject("LowerObject", controller),
        ReleaseObject("ReleaseObject", controller),
    ])
    return root
