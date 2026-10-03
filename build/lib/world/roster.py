"""Each location keeps the same residents from visit to visit."""
from entities.npcs.npc_generator import roll_npc_record


class NPCRoster:
    def __init__(self, world_state):
        self.world_state = world_state

    def for_location(self, location, job_counts, guild):
        """
        Records for ``job_counts`` ({job: headcount}) at ``location``. People met before come
        back; new slots get a resident rolled from their id, so the same id is the same person.
        Residents beyond today's headcount stay on file for when the map asks for them again.
        """
        stored = self.world_state.rosters.setdefault(location, [])
        used_ids = {record["id"] for record in stored}
        chosen = []
        for job, count in job_counts.items():
            records = [record for record in stored if record["job"] == job][:count]
            index = 1
            while len(records) < count:
                npc_id = f"{location}/{job}-{index:02d}"
                index += 1
                if npc_id in used_ids:
                    continue
                record = roll_npc_record(npc_id, job, guild)
                stored.append(record)
                used_ids.add(npc_id)
                records.append(record)
            chosen.extend(records)
        return chosen
