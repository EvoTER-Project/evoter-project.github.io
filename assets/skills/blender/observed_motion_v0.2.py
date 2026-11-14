"""Observable plane response to hand motion, independent of patch centroid drift."""
import numpy as np
from scipy.spatial.transform import Rotation


def compare_plane_response(before, after):
    result = dict(state='unknown', source='observed_plane_response_and_proprioception',
                  scope='normal displacement and plane attitude only; tangential slip and secure grasp are unverified')
    a,b = before.get('lid'), after.get('lid')
    if a is None or b is None:
        return dict(result,reason='selected plane must be observed at both times')
    if before['sim_time'] >= after['sim_time']:
        return dict(result,reason='no physical time interval')
    if not set(before['view_signature']) & set(after['view_signature']):
        return dict(result,reason='no common view of the same selected planar feature')
    for plane in (a,b):
        if plane['plane_rms_m'] > .002 or plane['inlier_fraction'] < .8 or min(plane['extent_m']) < .015:
            return dict(result,reason='insufficient planar fit quality or spatial support')
        if plane.get('normal_disagreement_deg',0) > 5:
            return dict(result,reason='inconsistent cross-view plane normals')
    n0,n1=np.array(a['normal']),np.array(b['normal'])
    if n0@n1 < 0:n1=-n1
    p0,p1=np.array(a['center']),np.array(b['center'])
    s0,s1=before['proprio'],after['proprio']
    e0,e1=np.array(s0['eef_pos']),np.array(s1['eef_pos'])
    rot=Rotation.from_quat(s1['eef_quat'])*Rotation.from_quat(s0['eef_quat']).inv()
    predicted=e1+rot.apply(p0-e0)
    pn=rot.apply(n0)
    angle=lambda x,y:float(np.rad2deg(np.arccos(np.clip(abs(x@y),-1,1))))
    stationary_angle,follow_angle=angle(n0,n1),angle(pn,n1)
    # A different visible center on the same plane leaves its plane equation unchanged.
    stationary=max(abs(float(n0@(p1-p0))),abs(float(n1@(p1-p0))))
    follow=abs(float(n1@(p1-predicted)))
    excitation=abs(float(n0@(predicted-p0)))
    tolerance=max(.004,3*a['plane_rms_m'],3*b['plane_rms_m'])
    result.update(normal_displacement_m=stationary,rigid_plane_error_m=follow,
                  normal_excitation_m=excitation,stationary_normal_angle_deg=stationary_angle,
                  follow_normal_angle_deg=follow_angle,tolerance_m=tolerance,
                  semantic_identity='agent must select the same physical plane, not merely parallel patches')
    if excitation < 4*tolerance:
        return dict(result,reason='insufficient normal excitation; tangential motion cannot test attachment')
    # Limit this simple test to short near-translational lifts/separations.
    if float(rot.magnitude()) > np.deg2rad(8):
        return dict(result,reason='large hand rotation requires full feature correspondence')
    if stationary < tolerance and stationary_angle < 3 and follow > 3*tolerance:
        return dict(result,state='release_supported',reason='selected plane stayed still as hand separated normally; inspect support and action context')
    if follow < tolerance and follow_angle < 3 and stationary > 3*tolerance:
        return dict(result,state='following_hand',reason='selected plane follows normal hand motion; tangential slip or hooking remain possible')
    return dict(result,reason='plane response does not distinguish stationary from hand-following')
