"""Version-bound assembly geometry and action-response verification tools."""
import uuid
import numpy as np
from PIL import Image, ImageDraw
from .atomic_tools import AtomicRoboCasaToolAdapter, Detection, _schema, _points, CAMERAS
from .tool_runtime import ToolSpec
from .assembly_geometry import plane_geometry, relative_geometry, compare_states


class ObservableAssemblyTools(AtomicRoboCasaToolAdapter):
    def _segment(self, query, camera, max_results, min_score):
        # Run vision in saved-image orientation; retain raw-coordinate masks for
        # compatibility with the existing depth backprojection contract.
        context=self.current_observation() if self.current_observation else None
        image=self._camera_image(camera)
        flipped=context is not None and context.get('image_orientation')=='top_down'
        if flipped:image=np.ascontiguousarray(image[::-1])
        output=self._sam3().call('sam3.segment_text',image=image,query=query,max_results=int(max_results))
        rows=[]
        for mask,score in zip(output.get('masks',[]),output.get('scores',[])):
            if float(score)<min_score:continue
            mask=np.asarray(mask,dtype=bool)
            if flipped:mask=np.ascontiguousarray(mask[::-1])
            ys,xs=np.where(mask)
            if not len(xs):continue
            key='det_'+uuid.uuid4().hex[:10]
            d=Detection(key,query,camera,mask,float(score),[int(xs.min()),int(ys.min()),int(xs.max()),int(ys.max())],
                        bool(xs.min()==0 or ys.min()==0 or xs.max()==mask.shape[1]-1 or ys.max()==mask.shape[0]-1),
                        observation_id=None if context is None else context['observation_id'],
                        source_sim_time=None if context is None else context['sim_time'])
            self.detections[key]=d;rows.append(self._detection_summary(d))
        return rows

    def register_all(self):
        super().register_all()
        self.assembly_states = {}
        region = dict(type='object', properties={
            'role':dict(type='string',enum=['lid','rim','handle']),
            'camera':dict(type='string',enum=list(CAMERAS)),
            'pixels':dict(type='array',minItems=3,items=dict(type='array',minItems=2,maxItems=2)),
            'sampling':dict(type='string',enum=['polygon','points'])},
            required=['role','camera','pixels','sampling'],additionalProperties=False)
        schema = _schema({
            'observation_id':dict(type='integer',minimum=1),
            'regions':dict(type='array',items=region),
            'lid_detection_ids':dict(type='array',items=dict(type='string')),
            'handle_detection_ids':dict(type='array',items=dict(type='string')),
        },required=['observation_id'])
        self.registry.register(ToolSpec('perception.estimate_assembly_geometry',
            'Estimate observed lid plane, handle and cup rim from current RGB-D. Select lid face polygons or SAM detections; rim requires visible rim boundary points (>=12 total over views), not a filled vessel mask. Coordinates follow saved PNG. Reports uncertainty; never assumes hidden geometry.',schema),
            self.estimate_assembly_geometry)
        self.registry.register(ToolSpec('verification.compare_assembly_states',
            'Compare two observed states around a physical action. Following-hand is evidence of hold OR hooking, not guaranteed secure grasp. No simulator contacts are used.',
            _schema({'before_id':dict(type='string'),'after_id':dict(type='string')},required=['before_id','after_id'])),
            self.compare_assembly_states)

    def _contact_evidence(self):
        # The inherited grasp macro must not consult _check_grasp in this campaign.
        return dict(contact_detected=None,object_attachment_evidence=False,
                    source='not_measured_use_visual_comparison',
                    gripper_open_fraction=float(self.bridge.get_gripper()))

    def estimate_assembly_geometry(self, observation_id, regions=None,
                                   lid_detection_ids=None, handle_detection_ids=None):
        version = self.get_observation_version(observation_id)
        current = self.current_observation()
        if current is None or abs(float(version['sim_time'])-float(current['sim_time'])) > 1e-8:
            return dict(error='refresh observation after motion',code='stale_observation')
        groups = {'lid':[], 'rim':[], 'handle':[]}
        views = {'lid':[], 'rim':[], 'handle':[]}
        for role, ids in [('lid',lid_detection_ids or []),('handle',handle_detection_ids or [])]:
            for key in ids:
                d = self.detections[key]
                if d.observation_id != observation_id:
                    return dict(error='detection version does not match',code='stale_detection')
                depth, intrinsics = self._saved_geometry(observation_id,d.camera,raw=True)
                p = _points(d.mask,depth,intrinsics)
                groups[role].append(p);views[role].append(d.camera)
        for region in regions or []:
            role, camera = region['role'],region['camera']
            depth, intrinsics = self._saved_geometry(observation_id,camera)
            pixels = np.asarray(region['pixels'],dtype=float)
            if not np.isfinite(pixels).all() or pixels.ndim!=2 or pixels.shape[1]!=2:
                raise ValueError('pixels must be finite xy pairs')
            h,w=depth.shape
            if (pixels<0).any() or (pixels[:,0]>=w).any() or (pixels[:,1]>=h).any():
                raise ValueError('region outside image; inspect saved PNG')
            if role=='rim' and region['sampling']!='points':
                raise ValueError('rim requires boundary points, not a filled polygon')
            if region['sampling']=='polygon':
                mask=Image.new('1',(w,h));ImageDraw.Draw(mask).polygon([tuple(p) for p in pixels],fill=1)
                p=_points(np.asarray(mask),depth,intrinsics)
            else:
                fx,fy,cx,cy,transform=intrinsics
                uv=np.rint(pixels).astype(int); z=depth[uv[:,1],uv[:,0]]
                valid=np.isfinite(z)&(z>.1)&(z<5)
                uv,z=uv[valid],z[valid]
                pc=np.c_[(uv[:,0]-cx)*z/fx,(uv[:,1]-cy)*z/fy,z]
                p=pc@transform[:3,:3].T+transform[:3,3]
            groups[role].append(p);views[role].append(camera)
        result=dict(observation_id=observation_id,sim_time=version['sim_time'],
                    lid=None,rim=None,handle=None,errors={},source='saved_rgbd_and_proprioception',
                    view_signature=sorted(set(views['lid'])),uncertainty_m=.004)
        for role in ('lid','rim'):
            if not groups[role]:
                continue
            try:
                geometry=plane_geometry(np.concatenate(groups[role]),rim=role=='rim')
                per_view=[]
                for p in groups[role]:
                    try:per_view.append(plane_geometry(p,rim=role=='rim'))
                    except ValueError:pass
                disagreement=max((np.linalg.norm(np.array(g['center'])-geometry['center']) for g in per_view),default=0.)
                geometry['view_count']=len(set(views[role]))
                geometry['center_disagreement_m']=float(disagreement)
                normal_disagreement=max((np.rad2deg(np.arccos(np.clip(abs(np.dot(g['normal'],geometry['normal'])),-1,1))) for g in per_view),default=0.)
                geometry['normal_disagreement_deg']=float(normal_disagreement)
                geometry['reliable']=(geometry['view_count']>=2 and len(per_view)>=2 and
                                      disagreement<.015 and normal_disagreement<5 and geometry['inlier_fraction']>.7)
                geometry['verification_status']='cross_view_consistent' if geometry['reliable'] else 'unverified_surface_selection'
                geometry['occlusion_limit']='visible extent may not equal full lid center' if role=='lid' else 'circle fit assumes circular visible rim'
                result[role]=geometry
                result['uncertainty_m']=max(result['uncertainty_m'],float(disagreement),geometry['plane_rms_m'],
                                             0 if geometry['reliable'] else .015)
            except ValueError as exc:result['errors'][role]=str(exc)
        if groups['handle']:
            p=np.concatenate(groups['handle'])
            if len(p)>=3:
                result['handle']=dict(center=np.median(p,axis=0).tolist(),n_points=len(p))
                if result['lid']:
                    d=np.array(result['handle']['center'])-result['lid']['center']
                    result['handle']['offset_from_visible_lid_center']=d.tolist()
        if result['lid'] and result['rim']:
            result['relative']=relative_geometry(result['lid'],result['rim'])
        result['proprio']=version['proprio']
        state_id='assembly_'+uuid.uuid4().hex[:10]
        result['state_id']=state_id
        self.assembly_states[state_id]=result
        return result

    def compare_assembly_states(self,before_id,after_id):
        before,after=self.assembly_states[before_id],self.assembly_states[after_id]
        return dict(before_id=before_id,after_id=after_id,**compare_states(before,after))
