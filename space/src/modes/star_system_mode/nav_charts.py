import math
import random

ORBIT_SAMPLES = 720
PIXELS_PER_DEGREE = 100  # wedge half-width grows with distance to the planet
MIN_HALF_WIDTH_DEG = 6
MAX_HALF_WIDTH_DEG = 45
STRONG_SIGNAL_PX = 700  # this close to a planet's rim or a station bay, the ping locks immediately

COMPASS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]


def _angle_diff(a, b):
    return abs((a - b + 180) % 360 - 180)


def _bearing(origin, point):
    return math.degrees(math.atan2(point[1] - origin[1], point[0] - origin[0]))


def _heading(bearing):
    """Screen-space bearing (0 = east, y down) to compass heading (0 = north, clockwise)."""
    heading = (bearing + 90) % 360
    return heading, COMPASS[int((heading + 22.5) // 45) % 8]


class NavCharts:
    """Tracks which bodies are charted, by id, and narrows uncharted planets via bearing pings."""

    def __init__(self, sun_position, charted):
        self.sun_position = sun_position
        self.charted = charted
        self.candidates = {}

    def is_charted(self, body):
        return body.id in self.charted

    def chart(self, body_id):
        self.charted.add(body_id)
        self.candidates.pop(body_id, None)

    def orbit_point(self, planet, index):
        theta = 2 * math.pi * index / ORBIT_SAMPLES
        return (
            self.sun_position[0] + planet.orbit_radius * math.cos(theta),
            self.sun_position[1] + planet.orbit_radius * math.sin(theta),
        )

    def ping(self, planet, origin):
        distance = math.dist(origin, planet.position)
        true_bearing = _bearing(origin, planet.position)
        half_width = min(max(distance / PIXELS_PER_DEGREE, MIN_HALF_WIDTH_DEG), MAX_HALF_WIDTH_DEG)
        # Offset stays within half the spread so the real bearing is always inside the wedge.
        reported = true_bearing + random.uniform(-half_width / 2, half_width / 2)
        heading, compass = _heading(reported)
        lines = [f"{planet.name}: bearing {heading:03.0f} ({compass}), spread {half_width:.0f} deg"]

        if distance - planet.radius <= STRONG_SIGNAL_PX:
            self.chart(planet.id)
            lines.append(f"Strong signal. {planet.name} charted, nav marker added.")
            return lines

        hits = {
            i for i in range(ORBIT_SAMPLES)
            if _angle_diff(_bearing(origin, self.orbit_point(planet, i)), reported) <= half_width
        }
        previous = self.candidates.get(planet.id)
        candidates = hits if previous is None else (previous & hits) or hits
        self.candidates[planet.id] = candidates

        arc_px = len(candidates) * 2 * math.pi * planet.orbit_radius / ORBIT_SAMPLES
        runs = self.candidate_runs(planet)
        # Once the remaining arc is no longer than the disk, flying to it finds the planet.
        if len(runs) == 1 and arc_px <= 2 * planet.radius:
            self.chart(planet.id)
            lines.append(f"Signal locked. {planet.name} charted, nav marker added.")
        elif len(runs) > 1:
            lines.append(f"Signal crosses the orbit in {len(runs)} places. Ping from another angle.")
        else:
            percent = 100 * len(candidates) / ORBIT_SAMPLES
            lines.append(f"Possible location: {percent:.0f}% of orbit. Get closer or ping from another angle.")
        return lines

    def ping_fixed(self, body, origin, point):
        """Bearing to a body that is not on an orbit. One ping charts it."""
        distance = math.dist(origin, point)
        true_bearing = _bearing(origin, point)
        half_width = min(max(distance / PIXELS_PER_DEGREE, MIN_HALF_WIDTH_DEG), MAX_HALF_WIDTH_DEG)
        reported = true_bearing + random.uniform(-half_width / 2, half_width / 2)
        heading, compass = _heading(reported)
        self.chart(body.id)
        lines = [
            f"{body.name}: bearing {heading:03.0f} ({compass}), spread {half_width:.0f} deg",
            f"Fixed contact. {body.name} charted, nav marker added.",
        ]
        if any(math.dist(origin, bay) <= STRONG_SIGNAL_PX for bay in body.access_points()):
            lines.append("Strong signal. Bay is in range.")
        return lines

    def candidate_runs(self, planet):
        """Contiguous runs of candidate orbit sample indices (wrapping around 360)."""
        candidates = self.candidates.get(planet.id)
        if not candidates:
            return []
        if len(candidates) == ORBIT_SAMPLES:
            return [list(range(ORBIT_SAMPLES))]
        runs = []
        for start in sorted(candidates):
            if (start - 1) % ORBIT_SAMPLES in candidates:
                continue
            run = [start]
            nxt = (start + 1) % ORBIT_SAMPLES
            while nxt in candidates:
                run.append(nxt)
                nxt = (nxt + 1) % ORBIT_SAMPLES
            runs.append(run)
        return runs
