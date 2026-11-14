---
name: observable-planar-seating
description: Recover an observed removable cover resting tilted or incompletely seated on a matching rim or support, using current RGB-D, grasp retention and separation evidence. Use for planar seating relations; not threaded, latched or force-fit closure.
metadata:
  category: manipulation
  tags: [robocasa365, planar-seating, observable-recovery, agent-driven]
---

# Observable Planar Seating

Use when a cover must rest with its seating face aligned to a matching, currently visible rim or support. This Skill guides Agent-driven atomic Tool use. It does not execute a graph or supply an autonomous assembly controller. Inputs are the live full task instruction, current RGB-D and proprioception, registered Tool schemas, and remaining episode budget. Output is a verified observable relation or the first unresolved gate; task success requires the runtime's official terminal signal.

Read only this runtime contract and current episode observations. Provenance and historical evidence are offline-only. Do not route on task names or seeds, replay poses, or obtain simulator contacts, hidden object transforms or partial success predicates.

For module-enabled execution, read [the two computation Tools' usage contract](references/tool-usage.md). It defines the current argument/output fields and the action-before/action-after comparison sequence. These are deterministic geometry/state computations, not separate decision Agents. The Agent selects visible semantic regions and interprets the evidence.

## Decide whether to intervene

Let a productive VLA rollout continue through checkpoints while the target remains visible and progresses toward the requested relation. A pause or a nonterminal result alone does not justify opening the fingers, withdrawing, or regrasping. Intervene on an observed failed relation: empty grasp, loss of retention, persistent tilted seating, or continued attachment during release. If evidence is missing, acquire a useful view before choosing the correction; missing detection is not proof that the object disappeared.

Call `policy.vla_act` with `horizon` bounded by the remaining episode budget and omit `instruction`. The runtime supplies the literal full task prompt. Checkpoints divide execution, not task semantics. After an external physical correction, refresh observations and use the runtime's current-history handback; do not replay pre-correction images. After joint control, call `motion.switch_controller` with `mode: osc` and require `safe: true` before VLA.

## Measure the seating face, not just a plausible plane

Use `observation.capture_all` and inspect wrist plus useful exterior views. When the catalog exposes `perception.estimate_assembly_geometry`, pass the current `observation_id` and image-derived `regions` with `role`, `camera`, `pixels`, and `sampling`. Use `role: lid` for the cover face. These are API role names, not permission to assume an unseen part. Pixel coordinates follow the saved observation image convention.

Select an interior planar patch whose relationship to the seating face is visually justified. Reject bevels, curved shoulders, mixed fixture/cover masks and finger surfaces even when plane residual is small. A raised planar grasp feature can support a normal estimate only when its parallel relationship to the cover is visible; its height and center are not the seating plane or object origin. Cross-view agreement supplements semantic selection; it cannot repair the same wrong selection in every view.

Treat face normal, visible patch center and rim center as separate estimates. A partially visible patch center drifts with occlusion and is not a whole-object center. Use rim boundary points with `role: rim` and `sampling: points`, not a filled vessel mask. Respect the catalog's boundary coverage and reliability checks. Without a valid destination estimate, acquire another view instead of inventing alignment offsets or insertion depth. Do not substitute gravity-level for alignment to a visibly tilted support.

## Correct only the failed relation

For persistent tilted seating, a reachable central grasp feature may permit a local regrasp without relocating the destination. Confirm pad clearance and the closing-axis fit from current views. Close, make a short clearance-limited lift, and observe that the same target leaves its support and follows the hand. An opening measurement or initial lift alone cannot distinguish a secure grasp from hooking. Check again after the first short transport or attitude correction; object rotation relative to the hand is evidence to reassess retention.

Where available, bracket one physical action with fresh geometry estimates and call `verification.compare_assembly_states` with `before_id` and `after_id`. Compare the same visible feature in the same world frame. `following_hand` can mean grip or hooking; `release_supported` is supporting evidence, not official completion. `unknown` is unresolved, not a passed gate. Raw motion values may support the Agent's judgment only together with current images and their uncertainty; record that distinction. If the feature is occluded, change the view or reacquire it before claiming retention or release.

Once retention and clearance are observed, correct the cover attitude relative to the support with a locally reachable motion. `motion.solve_ik` with the registered `scipy` backend followed by `motion.execute_joint_target` is an available route when appropriate; read the live quaternion convention and solution schema. Derive targets from current observations and measured hand/object relationship, never set an arbitrary wrist quaternion as a proxy for a level cover. Verify actual motion tracking and cover attitude. A rejected path calls for a new visibly clear approach or waypoint, not bypassing collision checks. Do not reuse the target after contact changes the cover's relationship to the hand.

Approach in short segments, preserving a confirmed grasp and checking face/rim alignment and visible support. Do not press through an uncertain contact or infer a hidden insertion depth from the top patch. If retention is unstable, return to a visible support when feasible and change the contact geometry rather than extending transport.

## Release, separate, then hand back

At an observably supported placement, open with `gripper.set`. Use a short, visibly clear separation motion and re-observe before a longer retreat. Require the cover to stay on the intended support as the hand moves away. If it follows the fingers, rotates or tips, stop that retreat and resolve attachment or support; opening wider and repeating the same retreat is not verification.

Recheck the cover attitude after release. Stable support and a flatter face do not prove that the task is complete. If the relation is stable, preserve it and allow a bounded full-task VLA continuation for remaining adjustment, with the controller handoff above. Stop immediately on `official_success: true` and `episode_finished: true`.

When a gate remains unresolved, preserve its observations and change the view, contact, approach or release hypothesis. The Skill never authorizes an episode reset or early failure declaration. Return the unresolved gate to the Agent's remaining-budget policy and continue permitted recovery until the campaign's actual terminal condition.

## Capability limits

Inspect the live catalog before using either optional computation module. If it is absent, visual judgment remains qualitative; do not report a computed normal or verified grasp/release. Current module rejection or `unknown` output must remain visible in the record. This contract does not repair perception, controller, or formal-isolation defects in the runtime. It does not claim measured gains beyond its development exemplars.
