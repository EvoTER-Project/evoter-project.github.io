# Geometry and grasp/release comparison Tools

Read the live catalog first. The fields below describe the inspected module implementation; report a schema mismatch to the supervisor rather than guessing an argument. All regions and identifiers come from the current episode. The Tool names are optional runtime capabilities, not implementations shipped by this Skill.

## 1. `perception.estimate_assembly_geometry`

Purpose: estimate an observed cover face, optional grasp feature and optional receiving rim. Use before attitude correction, around a short retention check, and after release. It does not decide a grasp or move the robot.

| Input | How to obtain it |
|---|---|
| `observation_id` (required integer) | Capture a fresh observation and use its returned identifier. |
| `regions` | List of regions selected on that observation's saved RGB images. |
| Region `camera` | Registered `agentview`, `agentview_left`, `agentview_right`, `agentview_center`, or `wrist`; use views actually supplied. |
| Region `role` | `lid` for the cover plane, `rim` for the receiving boundary, `handle` for the visible grasp feature. |
| Region `pixels` | Current image `[u,v]` points. At least three per region; geometry needs sufficient valid, non-collinear depth samples. Never reuse a past image's polygon after motion. |
| Region `sampling` | `polygon` for an interior planar cover patch; `points` for visible rim boundary samples. |
| `lid_detection_ids`, `handle_detection_ids` | Optional current segmentation alternatives after inspecting their semantic correctness; do not mix incompatible surfaces. |

For a rim estimate, the inspected implementation needs at least 12 usable boundary samples and broad arc coverage; it rejects an insufficiently circular or visible boundary. A filled vessel silhouette does not define its rim. Omit a currently hidden role and preserve the resulting missing estimate rather than fabricate points.

The current CLI syntax is `CLIENT call TOOL_NAME --arguments JSON`; use `CLIENT call --help` to check it before the first call.

Inspect `errors` and `lid`/`rim` availability before using numbers. For each plane inspect `normal_quality` (selected-surface attitude only), `reliable` (conservative combined geometry gate), `verification_status`, `view_count`, `plane_rms_m`, `normal_disagreement_deg`, and `center_disagreement_m` when present. Semantically wrong bevels can still produce a low residual and pass cross-view checks. Select the appropriate surface first.

`lid.normal` and `lid.tilt_deg` describe the selected surface. `tilt_deg` is relative to world vertical, not necessarily the receiving rim. When both surfaces are valid, the relative result's `normal_angle_deg` expresses their mismatch. `lateral_offset_m`, `lateral_distance_m`, and `plane_gap_m` refer to the measured visible surfaces. They are not exact object-origin offsets or a commanded insertion depth. A raised parallel feature may give an attitude cue without locating the actual seating face.

Retain returned `state_id` for the comparison Tool. Retain `observation_id`, `view_signature`, `uncertainty_m`, selected semantic feature and current images as its interpretation context. A state can be useful for qualitative diagnosis without being an accepted quantitative motion target.

## 2. `verification.compare_assembly_states`

Purpose: compare observed cover movement with hand movement across one known physical action. It uses the two saved geometry states and proprioception; it does not read simulator grasp/contact flags.

1. Capture and estimate the visible cover feature immediately before a bounded action; retain its `state_id` as `before_id`.
2. Execute the intended test action: a clearance-limited short lift for retention, or an opening and short separation motion for release. Choose its scale from current geometry; this document prescribes no fixed vector.
3. Capture again and estimate the same semantic feature with the at least one common camera. Select the same physical plane; different parallel features are not equivalent. Update pixels to its current location. Retain this new `state_id` as `after_id`.
4. Call with exactly `before_id` and `after_id`. Merely estimating twice without advancing physical time does not test attachment.

| Returned `state` | Interpretation and next decision |
|---|---|
| `following_hand` | Consistent with held motion **or hooking**. Check pad contact, clearance and continued retention in images before transport. |
| `release_supported` | The observed feature stayed still while the hand moved away. Confirm it is on the intended support and remains stable; this does not establish official success. |
| `slip_or_contact` | Motion differed from rigid hand-following. Stop extending transport/retreat, inspect contact or slip, and change the recovery hypothesis. |
| `stationary` / `object_moved` | Hand excitation was insufficient to distinguish holding from release. Do not label grasp/release verified. |
| `unknown` | Read `reason`: missing cover, changed views, no physical interval or excessive uncertainty. Acquire comparable evidence; do not pass the gate. |

The current implementation reports `normal_displacement_m`, `rigid_plane_error_m`, `normal_excitation_m`, plane-normal angle changes, `tolerance_m`, `scope`, and `reason`. It tests short near-translational lifts/separations with adequate normal excitation. The selected plane must have adequate area, low residual and stable orientation. It preserves `unknown` for narrow/poor fits, large rotations, tangential-only motion or ambiguous response.

A stationary plane while the hand lifts means a failed pickup during acquisition; after supported opening/separation it supports release. The API label `release_supported` alone does not determine that stage. `following_hand` describes normal plane response only: tangential slip, hooking and semantic identity remain for current-image verification. Do not call it a secure-grasp classifier.

`visible_centroid_diagnostic` contains the older visible-extent comparison for transparency. Its center shifts and uncertainty are not the new decision signal. Partial patch occlusion changes those centers even when the physical plane remains stationary. Single-view combined geometry can remain unreliable while the narrowly scoped plane-response test is usable; this never promotes full pose reliability.

The assembly sampler accepts finite positive metric depth up to its existing far limit, including near-wrist points below 10 cm. This does not validate mixed/background depth. Region selection remains the Agent's responsibility.

## Compose them in an episode

Use current VLA progress to choose checkpoints. Observe and estimate → identify a failed seating/retention relation → perform one justified bounded correction → observe and estimate again → compare when the correction tests retention or separation → inspect the resulting support and attitude. If the state is stable but the task is nonterminal, switch safely back to OSC when required and hand the complete goal back to VLA. The Agent owns this dynamic sequence; neither computation Tool is an action controller or official evaluator.
