---
name: constrained-insertion
description: Insert an observed held object through a visible opening or into a constrained receptacle, using fresh geometry and observable containment checks.
metadata:
  category: manipulation
  tags: [robocasa365, insertion, opening, containment]
---

# Constrained Insertion

Use this Skill when the object is already held and the destination is a narrow opening, slot, cup, dispenser, or other constrained receptacle. It is a relation-level capability, not a task script.

## Contract

Inputs are a fresh observation version, held-object evidence, destination opening geometry, and a relation such as `inside_opening` or `inside_receptacle`. Outputs are an observable insertion/containment postcondition or a bounded recovery code.

Before motion, obtain a fresh view of the opening and query geometry when available. Choose an approach that preserves clearance, aligns the held object's long axis with the opening, and uses short bounded approach segments. Do not use saved poses, task names, or a mask centroid as a placement target.

For a straight symmetric rod, either free end may establish insertion; require a particular end only when its shape or the goal makes that necessary.

After release, a projected segment beside a transparent receptacle does not by itself establish placement failure. Preserve the objects, complete bounded hand separation, and obtain a fresh independent view before choosing a regrasp. Use release_relation_ambiguous recovery while the relation remains unresolved; official completion remains authoritative.

Verify each gate: approach reached, object remained held, insertion progressed without contact stall, and the object is supported/contained before release. Release only after containment or support is observable; then retreat and refresh the observation.

Contact or slip can change the observed tip-to-TCP relation even while the object remains held. If the object tilts, the grasp opening changes, or insertion stalls, stop descent, unload the contact, and refresh the visible free end and opening before realignment; do not reuse the pre-contact offset.

Use `perception.query_geometry`, `perception.backproject_pixels`, `motion.servo_osc_pose`, `motion.move_delta`/`motion.approach_along_axis`, `gripper.set`, and fresh observation tools as registered. A failed insertion must change the hypothesis (view, alignment, depth, candidate, or route) before retrying.


## Optional current-geometry calculation

The geometry.py helper computes an axis-alignment rotation and TCP target from two currently observed held-segment points, the current TCP pose, and a desired free-end point. Choose the point order from the visible free end; the result is not a perception estimate. This corrects the rotated offset between the TCP and the insertion tip. Recompute after any changed grasp or base pose. Start above the opening with observed clearance, verify held identity and actual arrival, then descend in short checked segments. Support-plane points alone do not measure a transparent opening height. The helper performs no physical actions.

Input points must belong to the same current observation/world frame; quaternion order is XYZW. A missing, non-finite, zero-axis/zero-quaternion, or shorter-than-resolvable segment raises `ValueError`. Keep the held object and obtain a new view rather than inventing a target. A returned target is only a calculation: validate actual arrival and current held-end/opening relation through ordinary feedback, remeasure after contact or slip, and use the existing recovery rules when unresolved.
