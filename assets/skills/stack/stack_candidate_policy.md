# Frozen Candidate: Observable Assembly And VLA Handoff

This is a candidate policy for an agent-driven episode, not a validated success claim.

Use only the current episode's RGB-D, proprioception and non-privileged Tool results. Never read benchmark internals, GT, past episode artifacts or coordinates. Reconstruct geometry from fresh observations after motion.

Preserve the complete task goal in every VLA instruction. Start from the exact runtime task prompt. If current observations justify choosing an assembly order, append a concise relational instruction while retaining the final destination and object ordering. The runtime returns the exact effective instruction; check it.

When a goal combines containment and transport, test the source-assembly motif from observable_subgoal_sequence.md when its current visual and reachability preconditions hold. Verify stable assembly before transporting the composite. If those preconditions do not hold, choose a different ordering from current evidence.

Use VLA for perception-conditioned grasp and transport. Observe after bounded rollouts (up to 256 controller steps; shorten near contact/release). Keep continuous calls' history when no intervening motion occurred. After physical Tool intervention the runtime restarts the VLA observation history automatically.

Check the requested object-object relation separately from placement at the destination. Parallel placement, a vertical object leaning on a rim, or an object moving with an allegedly released gripper requires recovery. Stop blind continuation when the base drifts away from a local unresolved relation. Re-localize first.

For geometric recovery, choose visible rim/interior pixels rather than assuming a mask centroid or a center-plus-offset is suitable. Match the jaw closing direction to the local rim. Verify actual motion errors, object motion after lift, retention during transport, and separation after release. Do not infer a grasp from aperture alone. Empty grippers can hook an object and open fingers can remain trapped.

The OSC pose Tool does not guarantee orientation when quaternion_xyzw is null. Explicit orientation targets also require checking the achieved quaternion and stop reason. If a pose is not reached, change the reach/view/approach hypothesis. IK is an available alternative; execute only accepted solutions, verify physical tracking, and explicitly switch safely to OSC before returning to VLA. Do not repeat unsuccessful forced rotations at a constrained destination.

These are action-selection rules, not a coordinate script. No attempt may reset or read another episode. Official success and episode_finished must both be true. Otherwise continue meaningful recovery within the 5000-step total budget, preserving failures and calling the supervisor for lifecycle handling.

Images named agentview_*.png and wrist.png downloaded by control.py are upright display images. For backproject_pixels, convert display pixel (u,v) to raw (u,H-1-v); observation_id is an integer. Montage headers add 24 pixels and are not part of camera coordinates. Use individual camera images for pixel selection.
