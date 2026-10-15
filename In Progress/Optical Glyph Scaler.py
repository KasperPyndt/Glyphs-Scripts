# MenuTitle: Optical Glyph Scaler
# -*- coding: utf-8 -*-
"""Resize one glyph without accumulating edits; restore local stroke weight.

THESIS: Precision resizing from a frozen source, with verified compensation.
OWN-WORLD: Native macOS/Glyphs utility controls, system type and accent color.
STORY: Choose proportions, inspect an editor overlay, Apply or leave untouched.
FIRST VIEWPORT: Three slider/value rows, preview legend, status, Reset/Cancel/Apply.
FORM: Precisely specified native utility; inherited world, no concept seed.
FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, and DESIGN.md
"""

import math
import traceback
from GlyphsApp import Glyphs, GSLayer, GSPath, GSNode, LINE, CURVE, OFFCURVE, DRAWFOREGROUND, DRAWINACTIVE, UPDATEINTERFACE

TITLE = "Optical Glyph Scaler"
VERSION = "0.2.1"
EPS = 1e-7


class ScaleError(ValueError):
    pass


def point(node):
    return float(node.x), float(node.y)


def lerp(a, b, t):
    return tuple(a[k] + (b[k] - a[k]) * t for k in (0, 1))


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1]


def unit(v):
    length = math.hypot(*v)
    if length < EPS:
        raise ScaleError("A zero-length segment needs repairing before scaling.")
    return v[0] / length, v[1] / length


def cubic(p, t):
    u = 1 - t
    return tuple(u**3*p[0][k] + 3*u*u*t*p[1][k] + 3*u*t*t*p[2][k] + t**3*p[3][k] for k in (0, 1))


def tangent(p, t):
    u = 1 - t
    return tuple(3*u*u*(p[1][k]-p[0][k]) + 6*u*t*(p[2][k]-p[1][k]) + 3*t*t*(p[3][k]-p[2][k]) for k in (0, 1))


def fresh(paths, width=0):
    """New native layer: detached Glyphs layers can retain stale path caches."""
    result = GSLayer()
    for path in paths:
        result.shapes.append(path.copy())
    result.width = width
    return result


def bounds(layer):
    b = layer.bounds
    return b.origin.x, b.origin.y, b.size.width, b.size.height


def segments(layer):
    result = []
    for pi, path in enumerate(layer.paths):
        nodes = list(path.nodes)
        if not path.closed:
            raise ScaleError("Close open paths first. This version scales filled outlines.")
        start = next((i for i,n in enumerate(nodes) if n.type != OFFCURVE), None)
        if start is None:
            raise ScaleError("A contour has no on-curve nodes.")
        cycle = nodes[start:] + nodes[:start] + [nodes[start]]
        previous = 0
        for i in range(1, len(cycle)):
            if cycle[i].type == OFFCURVE:
                continue
            group = cycle[previous:i+1]
            curved = len(group) == 4 and all(n.type == OFFCURVE for n in group[1:-1])
            if len(group) != 2 and not curved:
                raise ScaleError("Only straight lines and cubic Béziers are supported; convert quadratic curves first.")
            a, b = point(group[0]), point(group[-1])
            pts = [point(n) for n in group] if curved else [a, lerp(a,b,1/3), lerp(a,b,2/3), b]
            if math.hypot(b[0]-a[0],b[1]-a[1]) < EPS and not curved:
                raise ScaleError("Remove duplicate consecutive nodes before scaling.")
            result.append((pi, [n.index for n in group], pts, curved))
            previous = i
    return result


def correct_directions(layer):
    """Containment, not overlap: Glyphs' generic fixer can invert one X arm."""
    samples = [[] for p in layer.paths]
    for pi,ids,ps,curved in segments(layer):
        samples[pi].extend(cubic(ps,t) for t in (0.,.25,.5,.75))
    paths = list(layer.paths)
    for i,path in enumerate(paths):
        depth = 0
        for j,other in enumerate(paths):
            if i==j:
                continue
            ink = other.bezierPath
            if all(ink.containsPoint_(p) for p in samples[i]):
                depth += 1
        wanted = -1 if depth%2==0 else 1
        if path.direction!=wanted:
            path.reverse()
    return layer


def ink_section(layer, p, t):
    """First filled interval along the local normal, not a bounding-box gap."""
    u = unit(t)
    n = (-u[1], u[0])
    ink = layer.bezierPath
    probe = .04
    filled = [bool(ink.containsPoint_((p[0]+n[0]*sign*probe,p[1]+n[1]*sign*probe))) for sign in (-1,1)]
    if filled[0] == filled[1]:
        return None  # Hidden overlap edge, or unsupported stroke style.
    sign = -1 if filled[0] else 1
    span = max(2000., 4*max(bounds(layer)[2:]))
    hits = layer.intersectionsBetweenPoints((p[0]-n[0]*span,p[1]-n[1]*span),(p[0]+n[0]*span,p[1]+n[1]*span))
    distances = sorted(((h.x-p[0])*n[0]+(h.y-p[1])*n[1])*sign for h in hits[1:-1])
    for d in distances:
        if d > .08 and not ink.containsPoint_((p[0]+n[0]*sign*(d+probe),p[1]+n[1]*sign*(d+probe))):
            return (p[0]+n[0]*sign*d,p[1]+n[1]*sign*d), d
    return None


def median(values):
    s = sorted(values)
    return s[len(s)//2] if s else None


def nearest_tangent(model,q):
    best = (float('inf'),None)
    for _,_,ps,_ in model:
        t = min((i/16. for i in range(17)),key=lambda t:(cubic(ps,t)[0]-q[0])**2+(cubic(ps,t)[1]-q[1])**2)
        step = 1/16.
        for _ in range(7):
            step /= 2
            t = min((max(0,t-step),t,min(1,t+step)),key=lambda t:(cubic(ps,t)[0]-q[0])**2+(cubic(ps,t)[1]-q[1])**2)
        p = cubic(ps,t)
        d = math.hypot(p[0]-q[0],p[1]-q[1])
        if d < best[0] and math.hypot(*tangent(ps,t))>EPS:
            best = d,unit(tangent(ps,t))
    return best[1]


def centerline_width(layer,model,p,tan,section=None):
    """Measure perpendicular to the mean tangent of the paired boundaries."""
    section = section or ink_section(layer,p,tan)
    if section is None:
        return None
    q,_ = section
    u = unit(tan)
    v = nearest_tangent(model,q)
    if v is None or abs(dot(u,v))<.8:
        return None
    if dot(u,v)<0:
        v = (-v[0],-v[1])
    middle = lerp(p,q,.5)
    along = unit((u[0]+v[0],u[1]+v[1]))
    n = (-along[1],along[0])
    span = 4*max(bounds(layer)[2:])+1000
    hits = layer.intersectionsBetweenPoints((middle[0]-n[0]*span,middle[1]-n[1]*span),(middle[0]+n[0]*span,middle[1]+n[1]*span))
    ds = sorted(dot((h.x-middle[0],h.y-middle[1]),n) for h in hits[1:-1])
    left,right = [d for d in ds if d<-.02],[d for d in ds if d>.02]
    if not left or not right or not layer.bezierPath.containsPoint_(middle):
        return None
    return min(right)-max(left)


def widths(layer, model):
    values = []
    for pi, indices, pts, curved in model:
        samples = []
        for t in (.35, .5, .65):
            section = ink_section(layer, cubic(pts,t), tangent(pts,t))
            if section:
                samples.append(section[1])
        values.append(median(samples))
    return values




def affine(source, fx, fy):
    result = fresh(source.paths, source.width)
    x,y,w,h = bounds(source)
    cx = x+w/2
    for path in result.paths:
        for node in path.nodes:
            node.x = cx+(node.x-cx)*fx
            node.y *= fy
    return fresh(result.paths,result.width)






def closest_location(model, q, allowed=None):
    """Find a boundary location, retaining its segment identity for tracking."""
    best = (float('inf'),None,None)
    for si,(_,_,ps,curved) in enumerate(model):
        if allowed is not None and si not in allowed:
            continue
        if not curved:
            d = (ps[-1][0]-ps[0][0],ps[-1][1]-ps[0][1])
            t = max(0.,min(1.,dot((q[0]-ps[0][0],q[1]-ps[0][1]),d)/max(EPS,dot(d,d))))
        else:
            t = min((i/20. for i in range(21)),key=lambda t:sum((cubic(ps,t)[k]-q[k])**2 for k in (0,1)))
            lo,hi = max(0.,t-.05),min(1.,t+.05)
            for _ in range(24):
                a,b = (2*lo+hi)/3,(lo+2*hi)/3
                da = sum((cubic(ps,a)[k]-q[k])**2 for k in (0,1))
                db = sum((cubic(ps,b)[k]-q[k])**2 for k in (0,1))
                if da<db:hi=b
                else:lo=a
            t = (lo+hi)/2
        p = cubic(ps,t)
        distance = math.hypot(p[0]-q[0],p[1]-q[1])
        if distance<best[0]:best = distance,si,t
    return best


def plane_parameter(ps, center, along, reference):
    """Intersect a tracked segment with the centerline's normal plane."""
    def f(t):
        p = cubic(ps,t)
        return dot((p[0]-center[0],p[1]-center[1]),along)
    t = reference
    for _ in range(12):
        value = f(t)
        if abs(value)<1e-5:return t
        derivative = dot(tangent(ps,t),along)
        if abs(derivative)<1e-7:break
        nxt = t-value/derivative
        if not 0<=nxt<=1:break
        t = nxt
    candidates=[]
    lo,fl = 0.,f(0.)
    for j in range(1,17):
        hi=j/16.;fh=f(hi)
        if fl*fh<=0:
            a,b=lo,hi
            for _ in range(22):
                m=(a+b)/2;fm=f(m)
                if fl*fm<=0:b=m
                else:a=m;fl=fm
            candidates.append((a+b)/2)
        lo,fl=hi,fh
    if not candidates:return None
    return min(candidates,key=lambda t:abs(t-reference))


def tracked_section(model, pair):
    """Re-measure on the SAME two edges, normal to their mean centerline.

    Parameters can slide along those edges, but never jump to a bar, serif or
    different bowl. This prevents a normal-ray intersection from changing the
    identity of the stroke halfway through compensation.
    """
    si,ta,sj,tb = pair[:4]
    a,b=model[si][2],model[sj][2]
    p,q=cubic(a,ta),cubic(b,tb)
    center=lerp(p,q,.5)
    for _ in range(4):
        u,v=unit(tangent(a,ta)),unit(tangent(b,tb))
        parallel=abs(dot(u,v))
        if parallel<.75:return None
        if dot(u,v)<0:v=(-v[0],-v[1])
        along=unit((u[0]+v[0],u[1]+v[1]))
        na,nb=plane_parameter(a,center,along,ta),plane_parameter(b,center,along,tb)
        if na is None or nb is None:return None
        ta,tb=na,nb
        p,q=cubic(a,ta),cubic(b,tb)
        center=lerp(p,q,.5)
    d=(q[0]-p[0],q[1]-p[1])
    n=(-along[1],along[0])
    if dot(d,n)<0:n=(-n[0],-n[1])
    thickness=dot(d,n)
    if thickness<=.08:return None
    return ta,tb,p,q,center,along,n,thickness,parallel


def stroke_pairs(source, model):
    pairs=[]
    for si,(_,_,ps,_) in enumerate(model):
        for t in (.2,.35,.5,.65,.8):
            p=cubic(ps,t);tan=tangent(ps,t)
            if math.hypot(*tan)<EPS:continue
            section=ink_section(source,p,tan)
            if section is None:continue
            # Check actual neighboring rays as well as tracked paired edges.
            # Keeping the opposite parameter fixed can halve a neighbor's
            # movement, accidentally leaving all three samples inside a join.
            nearby=[ink_section(source,cubic(ps,t+dt),tangent(ps,t+dt)) for dt in (-.045,.045)]
            if not all(v and .75<section[1]/v[1]<1.33 for v in nearby):continue
            distance,sj,tb=closest_location(model,section[0])
            if sj is None or si==sj or distance>.1:continue
            pair=(si,t,sj,tb)
            measured=tracked_section(model,pair)
            if measured is None:continue
            ta,tb,p,q,center,along,n,thickness,parallel=measured
            if parallel<.96 or min(ta,tb)<.08 or max(ta,tb)>.92:continue
            if not model[si][3] and not model[sj][3]:
                lengths=[math.hypot(model[j][2][-1][0]-model[j][2][0][0],model[j][2][-1][1]-model[j][2][0][1]) for j in (si,sj)]
                if thickness>min(lengths)*1.25:continue  # Caps/joins, not representative stroke sides.
            # Terminal cuts and joins are not representative stroke sections.
            if not source.bezierPath.containsPoint_(center):continue
            actual=ink_section(source,p,along)
            if actual is None or abs(actual[1]-thickness)>max(.35,thickness*.015):continue
            neighbor=[]
            for dt in (-.045,.045):
                test=tracked_section(model,(si,max(.001,min(.999,ta+dt)),sj,tb))
                if test:neighbor.append(test[7])
            if len(neighbor)<2 or not all(.75<thickness/v<1.33 for v in neighbor):continue
            if any(math.hypot(center[0]-r[5][0],center[1]-r[5][1])<max(1.,thickness*.08) and {si,sj}=={r[0],r[2]} for r in pairs):continue
            pairs.append((si,ta,sj,tb,thickness,center,parallel))
    if not pairs:raise ScaleError("No reliable paired stroke edges could be measured. Try ordinary scaling.")
    return pairs


def least_squares(rows, regularization, size):
    """Sparse, diagonally preconditioned normal solve; no numpy dependency."""
    diagonal=regularization[:]
    rhs=[0.]*size
    for cs,value,strength in rows:
        for i,c in cs:
            rhs[i]+=strength*c*value
            diagonal[i]+=strength*c*c
    def product(x):
        out=[regularization[i]*x[i] for i in range(size)]
        for cs,_,strength in rows:
            v=sum(c*x[i] for i,c in cs)*strength
            for i,c in cs:out[i]+=c*v
        return out
    x=[0.]*size;r=rhs[:]
    z=[r[i]/max(EPS,diagonal[i]) for i in range(size)];p=z[:]
    rz=sum(a*b for a,b in zip(r,z));initial=max(EPS,sum(v*v for v in rhs))
    for _ in range(min(600,size*5)):
        ap=product(p);den=sum(a*b for a,b in zip(p,ap))
        if den<EPS:break
        alpha=rz/den
        x=[a+alpha*b for a,b in zip(x,p)];r=[a-alpha*b for a,b in zip(r,ap)]
        if sum(v*v for v in r)<initial*1e-14:break
        z=[r[i]/max(EPS,diagonal[i]) for i in range(size)]
        new=sum(a*b for a,b in zip(r,z));beta=new/max(EPS,rz)
        p=[a+beta*b for a,b in zip(z,p)];rz=new
    return x




def flat_foot_levels(source):
    """Flat feet retain their authored vertical stations.

    A cap's two adjoining edges depart toward the same side. This excludes
    internal crossbars and smooth bowl extrema; counter contours are excluded
    too. Coordinates come from this source, not a guessed baseline or metric.
    Consequently raised feet, overshoots and descender levels stay intentional.
    """
    model=segments(source)
    incoming={(pi,ids[-1]):ps for pi,ids,ps,curved in model}
    outgoing={(pi,ids[0]):ps for pi,ids,ps,curved in model}
    levels={}
    for pi,ids,ps,curved in model:
        if curved or source.paths[pi].direction!= -1 or abs(ps[0][1]-ps[-1][1])>EPS:
            continue
        before=tangent(incoming[(pi,ids[0])],1.)
        after=tangent(outgoing[(pi,ids[-1])],0.)
        if min(math.hypot(*before),math.hypot(*after))<EPS:continue
        away_before=-unit(before)[1];away_after=unit(after)[1]
        if min(away_before,away_after)<.5:
            continue
        # A concave crossbar edge has the same corner pattern, but its ink
        # lies opposite the departing stem edges. It is not a terminal cap.
        middle=lerp(ps[0],ps[-1],.5);sign=1 if away_before>0 else -1
        ink=source.paths[pi].bezierPath
        if not ink.containsPoint_((middle[0],middle[1]+sign*.04)) or ink.containsPoint_((middle[0],middle[1]-sign*.04)):
            continue
        # In a separate horizontal bar, these are long stroke boundaries, not
        # its ends. Baseline/descender foot surfaces remain anchored even when
        # broad (e.g. a serif or an E's bottom arm).
        neighbors=[incoming[(pi,ids[0])],outgoing[(pi,ids[-1])]]
        longest=max(math.hypot(p[-1][0]-p[0][0],p[-1][1]-p[0][1]) for p in neighbors)
        if ps[0][1]>EPS and abs(ps[-1][0]-ps[0][0])>longest*1.25:continue
        for ni in ids:levels[(pi,ni)]=source.paths[pi].nodes[ni].y
    return levels


def validate_foot_levels(source,result,fy):
    for (pi,ni),y in flat_foot_levels(source).items():
        if abs(result.paths[pi].nodes[ni].y-y*fy)>1e-5:
            raise ScaleError("A flat stroke end lost its vertical alignment. Original outline is unchanged.")


def compensate(source,fx,fy,weight,numerical=False,level_scale=None):
    level_scale=fy if level_scale is None else level_scale
    outer=[(pi,p) for pi,p in enumerate(source.paths) if p.direction==-1]
    holes=[(pi,p) for pi,p in enumerate(source.paths) if p.direction==1]
    if len(outer)>1:
        groups=[[pi] for pi,p in outer]
        for hi,hole in holes:
            hb=hole.bounds;center=(hb.origin.x+hb.size.width/2,hb.origin.y+hb.size.height/2)
            matches=[(p.bounds.size.width*p.bounds.size.height,i) for i,(_,p) in enumerate(outer) if p.bezierPath.containsPoint_(center)]
            if not matches:raise ScaleError("A counter cannot be paired with its outer contour.")
            groups[min(matches)[1]].append(hi)
        center=bounds(source)[0]+bounds(source)[2]/2
        paths,reports=[None]*len(source.paths),[]
        for group in groups:
            part=fresh([source.paths[pi] for pi in group],source.width);pc=bounds(part)[0]+bounds(part)[2]/2
            out,report=compensate(part,fx,fy,weight,numerical=numerical,level_scale=level_scale)
            for pi,path in zip(group,out.paths):
                for node in path.nodes:node.x+=(pc-center)*(fx-1)
                paths[pi]=path
            reports.append(report)
        return fresh(paths,source.width),{"maxError":max(r['maxError'] for r in reports),"iterations":max(r['iterations'] for r in reports),"samples":sum(r['samples'] for r in reports)}
    sm=segments(source);pairs=stroke_pairs(source,sm)
    typical=median([r[4] for r in pairs])
    keys=[(pi,n.index) for pi,p in enumerate(source.paths) for n in p.nodes]
    index={key:i for i,key in enumerate(keys)};size=len(keys)*2
    def coefficients(si,t):
        pi,ids,_,curved=sm[si]
        values=((1-t)**3,3*(1-t)**2*t,3*(1-t)*t*t,t**3) if curved else (1-t,t)
        return [(index[(pi,i)],c) for i,c in zip(ids,values)]
    base=affine(source,fx,fy)
    levels={key:y*level_scale for key,y in flat_foot_levels(source).items()}
    fixed={2*index[key]+1 for key in levels}
    for (pi,ni),y in levels.items():base.paths[pi].nodes[ni].y=y
    base=fresh(base.paths,base.width);result=fresh(base.paths,base.width)
    # With authored endpoints fixed, the bowl's center reference is secondary
    # to its measured stroke weight. Do not fight the locked terminal stations.
    center_strength=.005 if levels else .02
    regularization=[.0003 if source.paths[pi].nodes[ni].type!=OFFCURVE else .0001 for pi,ni in keys for _ in (0,1)]
    baseflat=[v for pi,ni in keys for v in point(base.paths[pi].nodes[ni])]
    cx=bounds(source)[0]+bounds(source)[2]/2
    def evaluate(layer):
        model=segments(layer);measurements=[];missing=0
        for pair in pairs:
            section=tracked_section(model,pair)
            if section is None or not layer.bezierPath.containsPoint_(section[4]):
                missing+=1;continue
            desired=pair[4]*weight;tol=max(1.,desired*.015)
            measurements.append((pair,section,desired,tol))
        errors=[abs(s[7]-d) for _,s,d,_ in measurements]
        normalized=[e/m[3] for e,m in zip(errors,measurements)]
        score=sum(v*v for v in normalized)/max(1,len(normalized))+missing*10
        return model,measurements,missing,errors,normalized,score
    best_score=float('inf');best=None
    for iteration in range(28):
        model,measurements,missing,errors,normalized,score=evaluate(result)
        if score<best_score:best_score,best=score,fresh(result.paths,result.width)
        group_counts={}
        for pair in pairs:
            key=tuple(sorted((pair[0],pair[2])));group_counts[key]=group_counts.get(key,0)+1
        measured_groups={tuple(sorted((m[0][0],m[0][2]))) for m in measurements}
        covered=all(count<3 or group in measured_groups for group,count in group_counts.items())
        if covered and missing<=max(1,len(pairs)*.12) and len(measurements)>=len(pairs)*.88 and max(normalized,default=99)<=1:
            return result,{"maxError":max(errors,default=0.),"iterations":iteration+1,"samples":len(measurements),"omitted":missing,"tolerance":max(m[3] for m in measurements),"source":[m[0][4] for m in measurements],"final":[m[1][7] for m in measurements]}
        flat=[v for pi,ni in keys for v in point(result.paths[pi].nodes[ni])]
        rows=[]
        for pair,section,desired,tol in measurements:
            ta,tb,p,q,center,along,n,current,parallel=section
            ca,cb=coefficients(pair[0],ta),coefficients(pair[2],tb)
            # Differentiate the actual tracked measurement, not a frozen
            # boundary normal. In a modulated curve the measuring plane can
            # slide as handles move; ignoring that produced false failures.
            cs=[(2*i+k,-c*n[k]) for i,c in ca for k in (0,1)]+[(2*i+k,c*n[k]) for i,c in cb for k in (0,1)]
            if numerical:
                cs=[]
                for coordinate in sorted({2*i+k for i,c in ca+cb for k in (0,1)}):
                    nodekey=keys[coordinate//2];axis=coordinate%2;modified=list(model)
                    for si in (pair[0],pair[2]):
                        pi,ids,ps,curved=model[si]
                        if pi==nodekey[0] and nodekey[1] in ids:
                            ps=list(ps);j=ids.index(nodekey[1])
                            if curved:
                                probe_point=list(ps[j]);probe_point[axis]+=.05;ps[j]=tuple(probe_point)
                            else:
                                endpoints=[ps[0],ps[3]]
                                probe_point=list(endpoints[j]);probe_point[axis]+=.05;endpoints[j]=tuple(probe_point)
                                ps=[endpoints[0],lerp(endpoints[0],endpoints[1],1/3.),lerp(endpoints[0],endpoints[1],2/3.),endpoints[1]]
                            modified[si]=(pi,ids,ps,curved)
                    probe=tracked_section(modified,pair)
                    if probe:cs.append((coordinate,(probe[7]-current)/.05))
            # Paired correction moves both edges symmetrically, not independent
            # outline normals. The affine stroke center remains the reference.
            rows.append((cs,desired-current,1./max(1.,tol*tol)))
            reference=(cx+(pair[5][0]-cx)*fx,pair[5][1]*fy)
            for k in (0,1):
                cs=[(2*i+k,.5*c) for i,c in ca+cb]
                rows.append((cs,reference[k]-center[k],center_strength/max(1.,tol*tol)))
        def align(pi,a,b,u):
            n=(-u[1],u[0]);cs=[(2*index[(pi,a)]+k,-n[k]) for k in (0,1)]+[(2*index[(pi,b)]+k,n[k]) for k in (0,1)]
            rows.append((cs,-sum(c*flat[i] for i,c in cs),100.))
        for pi,ids,ps,curved in sm:
            if not curved:align(pi,ids[0],ids[-1],unit(((ps[-1][0]-ps[0][0])*fx,(ps[-1][1]-ps[0][1])*fy)))
        for pi,path in enumerate(result.paths):
            original=list(source.paths[pi].nodes);nodes=list(path.nodes)
            for i,node in enumerate(nodes):
                if node.type==OFFCURVE or not original[i].smooth:continue
                a,b=nodes[i-1],nodes[(i+1)%len(nodes)]
                oa,ob=original[i-1],original[(i+1)%len(nodes)]
                av,bv=(original[i].x-oa.x,original[i].y-oa.y),(ob.x-original[i].x,ob.y-original[i].y)
                if min(math.hypot(*av),math.hypot(*bv))<EPS or dot(unit(av),unit(bv))<.999:continue
                if a.type==OFFCURVE and b.type==OFFCURVE:u=unit((b.x-a.x,b.y-a.y))
                else:u=unit((av[0]*fx,av[1]*fy))
                if a.type==OFFCURVE:align(pi,a.index,i,u)
                if b.type==OFFCURVE:align(pi,i,b.index,u)
        # A small return-to-affine term regularizes unmeasured serif tips and
        # handles without forcing the bowl back to its uncompensated width.
        for i in range(size):rows.append(([(i,1.)],baseflat[i]-flat[i],regularization[i]*.15))
        # Fixed cap coordinates have zero displacement, not a soft preference.
        # Remove these degrees of freedom from every constraint before solving.
        if fixed:rows=[([(i,c) for i,c in cs if i not in fixed],v,s) for cs,v,s in rows]
        delta=least_squares(rows,regularization,size)
        limit=max(2.,typical*.16)
        peak=max((math.hypot(delta[i],delta[i+1]) for i in range(0,size,2)),default=0.)
        if peak>limit:delta=[v*limit/peak for v in delta]
        accepted=None
        for step in (1.,.5,.25,.125):
            trial=fresh(result.paths,result.width)
            for (pi,ni),i in index.items():
                node=trial.paths[pi].nodes[ni];node.x+=delta[2*i]*step;node.y+=delta[2*i+1]*step
            for (pi,ni),y in levels.items():trial.paths[pi].nodes[ni].y=y
            trial=fresh(trial.paths,trial.width)
            trial_score=evaluate(trial)[-1]
            if trial_score<score-1e-7:accepted=trial;break
        if accepted is None:break
        result=accepted
    _,measurements,missing,errors,normalized,_=evaluate(best)
    if missing>max(1,len(pairs)*.12):
        raise ScaleError("Too many stroke pairs became ambiguous at these settings. Reduce the change or turn off compensation.")
    raise ScaleError("Paired stroke compensation did not converge (error %.1f units). Reduce the change or turn off compensation."%max(errors,default=0.))


def validate_topology(source, result):
    """Reject flipped contours or counters escaping their original solid."""
    if len(source.paths)!=len(result.paths):
        raise ScaleError("Compensation changed the contour structure.")
    for original,candidate in zip(source.paths,result.paths):
        if original.direction!=candidate.direction:
            raise ScaleError("A contour collapsed or inverted. Reduce the change or turn off compensation.")
    sm,rm=segments(source),segments(result)
    def samples(model,pi):
        return [cubic(ps,t) for index,_,ps,curved in model if index==pi
                for t in ((0.,.25,.5,.75) if curved else (0.,.5))]
    for hi,hole in enumerate(source.paths):
        if hole.direction!=1:continue
        points=samples(sm,hi)
        parents=[(path.bounds.size.width*path.bounds.size.height,pi)
                 for pi,path in enumerate(source.paths) if path.direction==-1
                 and all(path.bezierPath.containsPoint_(p) for p in points)]
        if parents:
            pi=min(parents)[1]
            if not all(result.paths[pi].bezierPath.containsPoint_(p) for p in samples(rm,hi)):
                raise ScaleError("A counter no longer fits inside its outline. Reduce the change or turn off compensation.")


def scale_outline(source, height=100, width=100, weight=100, optical=True):
    if not source.paths:
        raise ScaleError("Choose a glyph with outlines. Components must be decomposed first.")
    if not all(math.isfinite(v) and 50 <= v <= 200 for v in (height,width,weight)):
        raise ScaleError("Enter percentages between 50 and 200.")
    source = fresh(source.paths,source.width)
    correct_directions(source)
    segments(source)  # Validate before any preview or mutation.
    fx,fy = width/100.,height/100.
    if optical and (fx,fy,weight)!=(1.,1.,100):
        sx,sy,sw,sh = bounds(source)
        # Fast paired-normal solve first. If its local approximation stalls,
        # retry from the same frozen outline using measured derivatives.
        # Both strategies must satisfy the SAME stroke and dimension checks.
        for numerical in (False,True):
            internal_x,internal_y = fx,fy
            try:
                for fit in range(24):
                    candidate,report = compensate(source,internal_x,internal_y,weight/100.,numerical=numerical,level_scale=fy)
                    tx,ty,tw,th = bounds(candidate)
                    if max(abs(tw-sw*fx),abs(th-sh*fy))<.6:
                        break
                    internal_x *= (sw*fx/tw)**.5
                    internal_y *= (sh*fy/th)**.5
                else:
                    raise ScaleError("The requested dimensions and stroke weight conflict. Try less compensation.")
                validate_topology(source,candidate)
                report['numericalRetry']=numerical
                break
            except ScaleError:
                if numerical:raise
        # Do not recenter away from authored foot landmarks. Outlines with
        # no such landmarks retain the existing round/overshoot placement.
        cy = 0. if flat_foot_levels(source) else (sy+sh/2)*fy-(ty+th/2)
        for path in candidate.paths:
            for node in path.nodes:
                node.y += cy
        candidate = fresh(candidate.paths,candidate.width)
    else:
        candidate,report = affine(source,fx,fy), {"maxError":0.,"iterations":0}
    sx,sy,sw,sh = bounds(source)
    tx,ty,tw,th = bounds(candidate)
    # Preserve the source's left/right spacing, not its old advance width.
    for path in candidate.paths:
        for node in path.nodes:
            node.x += sx-tx
    candidate = fresh(candidate.paths, source.width-sw+tw)
    validate_foot_levels(source,candidate,fy)
    validate_topology(source,candidate)
    return candidate,report


def signature(layer):
    return (float(layer.width),tuple((p.closed,tuple((n.x,n.y,n.type,n.smooth,str(n.name)) for n in p.nodes)) for p in layer.paths),tuple((a.name,a.position.x,a.position.y) for a in layer.anchors),tuple(str(c) for c in layer.components))


def finalized(candidate):
    result = fresh(candidate.paths,round(candidate.width))
    correct_directions(result)
    paths = []
    for path in result.paths:
        rounded_path = path.copy()
        nodes = []
        for node in path.nodes:
            # Re-create nodes: editing existing proxies can resurrect cached
            # fractional coordinates when the closing node is copied in G4.
            new = GSNode((round(node.x),round(node.y)),type=node.type)
            new.smooth = node.smooth
            for key in node.userData.keys():
                new.userData[key] = node.userData[key]
            nodes.append(new)
        rounded_path.nodes = nodes
        paths.append(rounded_path)
    return fresh(paths,round(result.width))


def open_panel():
    import vanilla
    import objc
    import GlyphsApp as host
    from AppKit import NSColor, NSGraphicsContext
    from Foundation import NSObject, NSTimer, NSRunLoop, NSRunLoopCommonModes

    try:
        ScalerTimer = objc.lookUpClass('OpticalGlyphScalerTimer')
    except objc.nosuchclass_error:
        class OpticalGlyphScalerTimer(NSObject):
            def fire_(self,timer):
                self.owner.compute()
        ScalerTimer = OpticalGlyphScalerTimer

    try:
        PercentageDelegate = objc.lookUpClass('OpticalGlyphScalerPercentageDelegateV2')
    except objc.nosuchclass_error:
        class OpticalGlyphScalerPercentageDelegateV2(vanilla.EditText.nsTextFieldDelegateClass):
            @objc.signature(objc._C_NSBOOL+b'@:@@:')
            def control_textView_doCommandBySelector_(self,control,editor,command):
                command=str(command)
                up=command in ('moveUp:','moveUpAndModifySelection:')
                down=command in ('moveDown:','moveDownAndModifySelection:')
                if not (up or down):return False
                event=Glyphs.currentEvent()
                shift=bool(event and int(event.modifierFlags()) & (1<<17)) or 'AndModifySelection' in command
                field=control.vanillaWrapper()
                try:value=float(editor.string().replace(',','.'))
                except ValueError:value=float(getattr(field.scalerOwner.w,field.axis).get())
                if not math.isfinite(value):value=100.
                value=max(50.,min(200.,value+(10 if shift else 1)*(1 if up else -1)))
                text='%g'%value
                field.set(text);editor.setString_(text)
                editor.setSelectedRange_((0,len(text)))
                field.scalerOwner.field_changed(field)
                return True
        PercentageDelegate = OpticalGlyphScalerPercentageDelegateV2

    class PercentageField(vanilla.EditText):
        nsTextFieldDelegateClass = PercentageDelegate

    class Controller:
        def __init__(self):
            self.timer = None
            self.timer_target = ScalerTimer.alloc().init()
            self.timer_target.owner = self
            self.source = None
            self.candidate = None
            self.closed = False
            self.drawing_error = False
            self.w = vanilla.FloatingWindow((420,320),TITLE,autosaveName="com.approximatetype.opticalGlyphScaler.window")
            self.w.glyph = vanilla.TextBox((18,16,180,22),"Choose a glyph")
            self.w.capture = vanilla.Button((-178,13,160,24),"Use selected glyph",callback=self.capture,sizeStyle="small")
            for name,label,y in (("height","Height",54),("width","Width",95),("weight","Weight",136)):
                setattr(self.w,name+'Label',vanilla.TextBox((18,y+3,52,20),label,sizeStyle="small"))
                slider = vanilla.Slider((78,y,237,24),minValue=50,maxValue=200,value=100,callback=self.slider_changed)
                slider.axis = name
                setattr(self.w,name,slider)
                field = PercentageField((327,y,55,24),"100",callback=self.field_changed)
                field.axis = name
                field.scalerOwner = self
                setattr(self.w,name+'Value',field)
                setattr(self.w,name+'Percent',vanilla.TextBox((385,y+4,18,18),"%",sizeStyle="small"))
                slider.getNSSlider().setAccessibilityLabel_(label+' percent')
                field.getNSTextField().setAccessibilityLabel_(label+' percent')
                field.getNSTextField().setToolTip_("Up/Down: 1%. Shift+Up/Down: 10%. Range 50–200%.")
            self.w.optical = vanilla.CheckBox((18,177,280,20),"Preserve local stroke weight",value=True,callback=self.changed,sizeStyle="small")
            self.w.legend = vanilla.TextBox((18,201,-18,16),"Gray outline: original · Filled outline: preview",sizeStyle="mini")
            self.w.status = vanilla.TextBox((18,225,-18,46),"",sizeStyle="small")
            self.w.reset = vanilla.Button((18,-37,65,24),"Reset",callback=self.reset,sizeStyle="small")
            self.w.cancel = vanilla.Button((-168,-37,65,24),"Cancel",callback=self.cancel,sizeStyle="small")
            self.w.apply = vanilla.Button((-83,-37,65,24),"Apply",callback=self.apply,sizeStyle="small")
            self.w.apply.enable(False)
            self.w.cancel.getNSButton().setKeyEquivalent_('\x1b')
            self.w.height.getNSSlider().setToolTip_("50% is half the original ink height; 200% is twice the height. Baseline stays anchored.")
            self.w.weight.getNSSlider().setToolTip_("100% restores original local stroke thickness after resizing. 110% targets strokes 10% heavier.")
            self.w.setDefaultButton(self.w.apply)
            self.w.bind("close",self.close)
            self.capture(None)
            Glyphs.addCallback(self.opticalScalerDrawPreview,DRAWFOREGROUND)
            Glyphs.addCallback(self.opticalScalerDrawPreview,DRAWINACTIVE)
            self.w.open()
            self.w.getNSWindow().setHidesOnDeactivate_(True)

        def stop_timer(self):
            if self.timer is not None:
                self.timer.invalidate()
                self.timer = None

        def capture(self,sender):
            self.stop_timer()
            self.candidate = None
            self.source = None
            self.w.glyph.set("Choose a glyph")
            font = Glyphs.font
            layers = list(font.selectedLayers) if font else []
            if len(layers)!=1:
                self.source = None
                self.w.status.set("Select one glyph in the current master, then Use selected glyph.")
                self.w.apply.enable(False)
                Glyphs.redraw()
                return
            layer = layers[0]
            if not layer.isMasterLayer or layer.layerId!=font.selectedFontMaster.id:
                self.source = None
                self.w.status.set("Choose the current master layer, not a background or alternate layer.")
                self.w.apply.enable(False)
                return
            if layer.components or layer.hints:
                self.source = None
                self.w.status.set("Use unhinted outlines. Decompose components first, or scale a copy.")
                self.w.apply.enable(False)
                return
            self.font,self.target = font,layer
            self.original_signature = signature(layer)
            self.source = fresh(layer.paths,layer.width)
            self.source_anchors = [a.copy() for a in layer.anchors]
            self.w.glyph.set(layer.parent.name+' · '+font.selectedFontMaster.name)
            self.reset(None)

        def reset(self,sender):
            self.stop_timer()
            for name in ('height','width','weight'):
                getattr(self.w,name).set(100)
                getattr(self.w,name+'Value').set('100')
            self.compute()

        def slider_changed(self,sender):
            value = round(sender.get())
            getattr(self.w,sender.axis+'Value').set(str(value))
            self.changed(sender)

        def field_changed(self,sender):
            try:
                value = float(sender.get().replace(',','.'))
                if 50<=value<=200:
                    getattr(self.w,sender.axis).set(value)
            except ValueError:
                pass
            self.changed(sender)

        def changed(self,sender):
            self.stop_timer()
            self.candidate = None
            self.w.apply.enable(False)
            self.w.weight.enable(self.w.optical.get())
            self.w.weightValue.enable(self.w.optical.get())
            if self.source is None:
                Glyphs.redraw()
                return
            self.w.status.set("Preparing preview…")
            self.timer = NSTimer.timerWithTimeInterval_target_selector_userInfo_repeats_(.18,self.timer_target,'fire:',None,False)
            NSRunLoop.mainRunLoop().addTimer_forMode_(self.timer,NSRunLoopCommonModes)
            Glyphs.redraw()

        def valid_source(self):
            return self.source is not None and Glyphs.font==self.font and signature(self.target)==self.original_signature

        def compute(self):
            self.stop_timer()
            self.candidate = None
            self.w.apply.enable(False)
            if self.source is None:
                if self.w.status.get()=="Preparing preview…":
                    self.w.status.set("Select one glyph in the current master, then Use selected glyph.")
                return
            if not self.valid_source():
                self.w.status.set("The source or active font changed. Use selected glyph to start again.")
                Glyphs.redraw()
                return
            try:
                values = [float(getattr(self.w,n+'Value').get().replace(',','.')) for n in ('height','width','weight')]
                if not self.w.optical.get():
                    values[2] = 100.
                result,report = scale_outline(self.source,*values,optical=self.w.optical.get())
                for name,value in zip(('height','width','weight'),values):
                    getattr(self.w,name).set(value)
                self.candidate,self.report,self.values = result,report,values
                self.w.apply.enable(values[:2]!=[100.,100.] or (self.w.optical.get() and values[2]!=100.))
                b = bounds(result)
                self.w.status.set("Preview: %.0f × %.0f units. %s" % (b[2],b[3],"Stroke weight checked." if self.w.optical.get() else "Ordinary scaling; strokes resize too."))
            except (ScaleError,ValueError) as e:
                message = str(e) if isinstance(e,ScaleError) else "Enter a number between 50 and 200 for each control."
                self.w.status.set(message if len(message)<125 else "Cannot preserve strokes at these settings. Reduce the change, or switch off stroke preservation.")
                self.w.status.getNSTextField().setToolTip_(message)
            except Exception:
                self.w.status.set("Preview failed. Original outline is unchanged; see Macro Panel.")
                print(traceback.format_exc())
            Glyphs.redraw()

        def opticalScalerDrawPreview(self,layer,info):
            if self.closed or self.candidate is None or not self.valid_source() or layer!=self.target:
                return
            try:
                scale = max(.01,float(info.get('Scale',1.)))
                NSGraphicsContext.saveGraphicsState()
                # Repaint only the original ink; no font data or background layer
                # is modified. A thin gray outline remains behind the result.
                original = self.source.bezierPath.copy()
                NSColor.textBackgroundColor().set()
                original.fill()
                original.setLineWidth_(2.5/scale)
                original.stroke()
                NSColor.secondaryLabelColor().set()
                original.setLineWidth_(.75/scale)
                original.stroke()
                NSColor.labelColor().set()
                self.candidate.bezierPath.fill()
                NSGraphicsContext.restoreGraphicsState()
            except Exception:
                NSGraphicsContext.restoreGraphicsState()
                if not self.drawing_error:
                    self.drawing_error = True
                    print(traceback.format_exc())

        def apply(self,sender):
            self.compute()
            if self.candidate is None or not self.valid_source() or not self.w.apply.getNSButton().isEnabled():
                return
            result = finalized(self.candidate)
            sx,sy,sw,sh = bounds(self.source)
            tx,ty,tw,th = bounds(self.candidate)
            # Anchors follow the requested affine dimensions, including the
            # translation that preserves the original sidebearings.
            fy,fx = self.values[0]/100.,self.values[1]/100.
            anchor_shift = sx-(sx+sw/2-sw*fx/2)
            glyph = self.target.parent
            glyph.beginUndo()
            try:
                self.target.shapes = [p.copy() for p in result.paths]
                self.target.width = result.width
                self.target.selection = []
                for a,original in zip(self.target.anchors,self.source_anchors):
                    a.position = (round((sx+sw/2)+(original.position.x-(sx+sw/2))*fx+anchor_shift),round(original.position.y*fy))
            finally:
                glyph.endUndo()
            self.w.getNSWindow().performClose_(None)
            Glyphs.redraw()

        def cancel(self,sender):
            self.w.getNSWindow().performClose_(None)

        def close(self,sender):
            self.closed = True
            self.stop_timer()
            Glyphs.removeCallback(self.opticalScalerDrawPreview)
            self.candidate = None
            self.timer_target.owner = None
            for name in ('height','width','weight'):
                getattr(self.w,name+'Value').scalerOwner = None
            Glyphs.redraw()
            if getattr(host,'opticalGlyphScaler',None) is self:
                host.opticalGlyphScaler = None

    old = getattr(host,'opticalGlyphScaler',None)
    if old is not None and not old.closed:
        old.w.getNSWindow().performClose_(None)
    controller = Controller()
    host.opticalGlyphScaler = controller
    return controller


if __name__ == '__main__':
    open_panel()
