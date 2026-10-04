"""Pure rectangle operations on normalized cm. No search, repair or defaults."""
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Rectangle:
    x: Decimal
    y: Decimal
    width: Decimal
    depth: Decimal

    @property
    def right(self) -> Decimal:
        return self.x + self.width

    @property
    def bottom(self) -> Decimal:
        return self.y + self.depth


def rotated(x: Decimal, y: Decimal, width: Decimal, depth: Decimal,
            rotation: Decimal) -> Rectangle:
    # x/y denote minimum corner of the ROTATED bounding box, never its centre.
    if rotation in (90, 270):
        width, depth = depth, width
    return Rectangle(x, y, width, depth)


def contained(inner: Rectangle, outer: Rectangle) -> bool:
    return (inner.x >= outer.x and inner.y >= outer.y
            and inner.right <= outer.right and inner.bottom <= outer.bottom)


def intersects(a: Rectangle, b: Rectangle) -> bool:
    # Strict positive-area overlap. Touching edges is not overlap.
    return (max(a.x, b.x) < min(a.right, b.right)
            and max(a.y, b.y) < min(a.bottom, b.bottom))


def clearance(item: Rectangle, room: Rectangle, obstacles: list[Rectangle],
              side: str) -> Decimal:
    """Free distance sweeping the item's entire face along a global axis.

    Only obstacles with positive transverse overlap restrict that face. This
    is a rectangular reservation check, not a human route/accessibility test.
    """
    gaps = {"left": item.x - room.x, "right": room.right - item.right,
            "top": item.y - room.y, "bottom": room.bottom - item.bottom}
    gap = gaps[side]
    for obstacle in obstacles:
        if intersects(item, obstacle):
            # An already occupied footprint has no free operating clearance,
            # including obstacles fully contained inside the item's rectangle.
            gap = min(gap, Decimal(0))
            continue
        if side in ("left", "right"):
            across = max(item.y, obstacle.y) < min(item.bottom, obstacle.bottom)
            if not across:
                continue
            if side == "right" and obstacle.right > item.right:
                gap = min(gap, max(Decimal(0), obstacle.x - item.right))
            elif side == "left" and obstacle.x < item.x:
                gap = min(gap, max(Decimal(0), item.x - obstacle.right))
        else:
            across = max(item.x, obstacle.x) < min(item.right, obstacle.right)
            if not across:
                continue
            if side == "bottom" and obstacle.bottom > item.bottom:
                gap = min(gap, max(Decimal(0), obstacle.y - item.bottom))
            elif side == "top" and obstacle.y < item.y:
                gap = min(gap, max(Decimal(0), item.y - obstacle.bottom))
    return gap
