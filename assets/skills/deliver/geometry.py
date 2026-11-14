"""Pure geometry from current observed points and TCP; no perception or actions."""
import numpy as np


def _finite_vector(value, length, label):
    try:
        vector = np.asarray(value, dtype=float)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be a finite {length}-vector") from exc
    if vector.shape != (length,) or not np.isfinite(vector).all():
        raise ValueError(f"{label} must be a finite {length}-vector")
    return vector


def align_free_end(segment_near, segment_tip, tcp_position, tcp_quaternion_xyzw,
                   tip_goal, target_axis=(0., 0., -1.)):
    """Rotate the measured free-end axis and offset to a caller-chosen goal.

    Points use one current world frame in metres; quaternion order is XYZW.
    The caller establishes point identity, opening clearance and freshness.
    Unknown/degenerate inputs raise ValueError and produce no motion target.
    """
    near = _finite_vector(segment_near, 3, "segment_near")
    tip = _finite_vector(segment_tip, 3, "segment_tip")
    tcp = _finite_vector(tcp_position, 3, "tcp_position")
    goal = _finite_vector(tip_goal, 3, "tip_goal")
    axis = tip - near
    length = np.linalg.norm(axis)
    if not np.isfinite(length) or length < .005:
        raise ValueError("Observed segment is too short or unresolved")
    u = axis / length
    v = _finite_vector(target_axis, 3, "target_axis")
    norm = np.linalg.norm(v)
    if not np.isfinite(norm) or norm <= 1e-12:
        raise ValueError("target_axis must be nonzero")
    v = v / norm
    q = _finite_vector(tcp_quaternion_xyzw, 4, "tcp_quaternion_xyzw")
    norm = np.linalg.norm(q)
    if not np.isfinite(norm) or norm <= 1e-12:
        raise ValueError("tcp_quaternion_xyzw must be nonzero")
    q = q / norm
    cross = np.cross(u, v)
    dot = np.clip(np.dot(u, v), -1., 1.)
    if dot < -1. + 1e-8:
        basis = np.eye(3)[np.argmin(np.abs(u))]
        a = np.cross(u, basis)
        a /= np.linalg.norm(a)
        delta = np.r_[a, 0.]
    else:
        delta = np.r_[cross, 1. + dot]
        delta /= np.linalg.norm(delta)
    a, w = delta[:3], delta[3]
    offset = tip - tcp
    rotated_offset = offset + 2 * np.cross(a, np.cross(a, offset) + w * offset)
    b, z = q[:3], q[3]
    newq = np.r_[w*b + z*a + np.cross(a, b), w*z - np.dot(a, b)]
    target = goal - rotated_offset
    if not np.isfinite(target).all() or not np.isfinite(newq).all():
        raise ValueError("Input geometry did not produce a finite target")
    return {"position": target.tolist(), "quaternion_xyzw": newq.tolist(),
            "quaternion_wxyz": np.r_[newq[3], newq[:3]].tolist(),
            "segment_length_m": float(length), "tip_goal": goal.tolist()}
