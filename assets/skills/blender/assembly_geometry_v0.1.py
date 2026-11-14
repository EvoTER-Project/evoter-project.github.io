"""Assembly evidence from observed points only; no simulator or object models."""
import numpy as np
from scipy.spatial import ConvexHull
from scipy.spatial.transform import Rotation


def plane_geometry(points, *, rim=False):
    points = np.asarray(points, dtype=float).reshape(-1, 3)
    points = points[np.isfinite(points).all(axis=1)]
    if len(points) < 12:
        raise ValueError('at least 12 valid surface points are required')
    # Equalize pixel sampling density before fitting, deterministic across runs.
    _, ids = np.unique(np.round(points / .0015).astype(int), axis=0, return_index=True)
    points = points[np.sort(ids)]
    if len(points) < 12:
        raise ValueError('insufficient spatially distinct points')
    if len(points) > 3000:
        points = points[np.linspace(0, len(points)-1, 3000).astype(int)]
    rng = np.random.default_rng(0)
    best = np.zeros(len(points), dtype=bool)
    for _ in range(160):
        a, b, c = points[rng.choice(len(points), 3, replace=False)]
        n = np.cross(b-a, c-a)
        if np.linalg.norm(n) < 1e-8:
            continue
        n /= np.linalg.norm(n)
        mask = np.abs((points-a) @ n) < .003
        if mask.sum() > best.sum():
            best = mask
    if best.sum() < 12 or best.mean() < .55:
        raise ValueError('no dominant plane; select the actual lid face or cup rim')
    p = points[best]
    mean = p.mean(axis=0)
    _, singular, axes = np.linalg.svd(p-mean, full_matrices=False)
    if singular[1] / max(singular[0], 1e-9) < .12:
        raise ValueError('surface points are nearly collinear')
    normal = axes[2]
    if normal[2] < 0:
        normal = -normal
    basis = axes[:2].T
    xy = (p-mean) @ basis
    hull = xy[ConvexHull(xy).vertices]
    lo, hi = np.quantile(xy, [.01, .99], axis=0)
    center_2d = (lo+hi)/2
    residual = float(np.sqrt(np.mean(((p-mean) @ normal)**2)))
    result = dict(normal=normal.tolist(), plane_rms_m=residual,
                  inlier_fraction=float(best.mean()), n_points=len(points),
                  extent_m=(hi-lo).tolist(), center_kind='visible_surface_extent_center')
    if rim:
        # Rim inputs must identify the boundary, not the whole vessel/disk.
        # Fit all boundary samples rather than a filled-mask centroid.
        a = np.c_[2*xy, np.ones(len(xy))]
        cx, cy, k = np.linalg.lstsq(a, (xy*xy).sum(axis=1), rcond=None)[0]
        radius = float(np.sqrt(max(0, k+cx*cx+cy*cy)))
        radial = np.linalg.norm(xy-[cx,cy], axis=1)
        circle_rms = float(np.sqrt(np.mean((radial-radius)**2)))
        angles = np.sort(np.arctan2(xy[:,1]-cy, xy[:,0]-cx))
        coverage = float(2*np.pi-np.diff(np.r_[angles, angles[0]+2*np.pi]).max())
        if radius < .015 or radius > .25 or circle_rms > max(.003, .06*radius) or coverage < np.deg2rad(200):
            raise ValueError('rim not sufficiently circular/visible; use boundary points from multiple views')
        center_2d = np.array([cx, cy])
        result.update(center_kind='observed_rim_circle_center', radius_m=radius,
                      circle_rms_m=circle_rms, angular_coverage_deg=float(np.rad2deg(coverage)))
    result['center'] = (mean+basis @ center_2d).tolist()
    result['tilt_deg'] = float(np.rad2deg(np.arccos(np.clip(normal[2], -1, 1))))
    return result


def relative_geometry(lid, rim):
    delta = np.array(lid['center'])-rim['center']
    n = np.array(rim['normal'])
    height = float(delta @ n)
    lateral = delta-height*n
    return dict(lateral_offset_m=lateral.tolist(), lateral_distance_m=float(np.linalg.norm(lateral)),
                plane_gap_m=height,
                normal_angle_deg=float(np.rad2deg(np.arccos(np.clip(np.dot(lid['normal'],n),-1,1)))),
                interpretation='visible lid face versus visible rim, not simulator object origins')


def compare_states(before, after):
    a, b = before['lid'], after['lid']
    if a is None or b is None:
        return dict(state='unknown', reason='lid must be observed at both times')
    uncertainty = max(before['uncertainty_m'], after['uncertainty_m'], .004)
    p0, p1 = np.array(a['center']), np.array(b['center'])
    s0, s1 = before['proprio'], after['proprio']
    e0, e1 = np.array(s0['eef_pos']), np.array(s1['eef_pos'])
    rotation = Rotation.from_quat(s1['eef_quat']) * Rotation.from_quat(s0['eef_quat']).inv()
    predicted = e1+rotation.apply(p0-e0)
    movement = float(np.linalg.norm(p1-p0))
    eef_movement = float(np.linalg.norm(e1-e0))
    rigid_error = float(np.linalg.norm(p1-predicted))
    normal_change = float(np.rad2deg(np.arccos(np.clip(np.dot(a['normal'], b['normal']),-1,1))))
    gap0, gap1 = float(s0['gripper_open']), float(s1['gripper_open'])
    result = dict(lid_motion_m=movement,eef_motion_m=eef_movement,rigid_follow_error_m=rigid_error,
                  normal_change_deg=normal_change,aperture_before=gap0,aperture_after=gap1,
                  uncertainty_m=uncertainty,source='observed_surface_motion_and_proprioception')
    if before['sim_time'] >= after['sim_time']:
        return dict(**result,state='unknown',reason='no physical time interval')
    if before['view_signature'] != after['view_signature']:
        return dict(**result,state='unknown',reason='view selection changed; centroid shift may be visibility bias')
    if uncertainty > .012:
        return dict(**result,state='unknown',reason='geometry disagreement too large')
    if eef_movement < 3*uncertainty:
        return dict(**result,state='stationary' if movement < 2*uncertainty and normal_change < 4 else 'object_moved',
                    reason='insufficient hand motion to distinguish attachment from release')
    if movement < 2*uncertainty and rigid_error > 2*uncertainty:
        return dict(**result,state='release_supported',reason='hand moved away while observed lid stayed still')
    if rigid_error < 2*uncertainty and movement > 2*uncertainty:
        return dict(**result,state='following_hand',reason='consistent with hold or residual hooking; not proof of secure grasp')
    return dict(**result,state='slip_or_contact',reason='object motion differs from rigid hand-following; inspect views')
