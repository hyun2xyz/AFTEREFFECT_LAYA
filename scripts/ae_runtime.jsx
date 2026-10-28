(function () {
    var job = /*__AE_BASIC_JOB__*/;
    var dir = new File($.fileName).parent;
    var resultFile = new File(dir.fsName + "/result.json");
    var startedFile = new File(dir.fsName + "/started.json");
    var report = {schema: "ae-basic.v1", job_id: job.job_id, ae_version: app.version, status: "failed", actions: []};
    var refs = {}, undo = false;
    var matches = {position:"ADBE Position", anchor_point:"ADBE Anchor Point", scale:"ADBE Scale", rotation:"ADBE Rotate Z", opacity:"ADBE Opacity"};

    function encode(v) {
        if (v === null || v === undefined) return "null";
        if (typeof v === "string") return '"' + v.replace(/\\/g,"\\\\").replace(/"/g,'\\"').replace(/[\x00-\x1f\u2028\u2029]/g,function(c){return "\\u"+("0000"+c.charCodeAt(0).toString(16)).slice(-4);}) + '"';
        if (typeof v === "number") return isFinite(v) ? String(v) : "null";
        if (typeof v === "boolean") return v ? "true" : "false";
        var pieces = [], i, k;
        if (v instanceof Array) {for(i=0;i<v.length;i++) pieces.push(encode(v[i])); return "["+pieces.join(",")+"]";}
        for(k in v) if(v.hasOwnProperty(k)) pieces.push(encode(k)+":"+encode(v[k]));
        return "{"+pieces.join(",")+"}";
    }
    function write(file, value) {
        file.encoding = "UTF-8";
        if(!file.open("w")) throw Error("Cannot write receipt. Enable Allow Scripts To Write Files And Access Network in AE settings: "+file.error);
        try {if(!file.write(encode(value))) throw Error("Receipt write failed: "+file.error);} finally {file.close();}
    }
    function hash(s) {var h=2166136261;for(var i=0;i<s.length;i++){h ^= s.charCodeAt(i);h += (h<<1)+(h<<4)+(h<<7)+(h<<8)+(h<<24);}return (h>>>0).toString(16)+":"+s.length;}
    function prop(layer, name) {
        var p=layer.property("ADBE Transform Group").property(matches[name]);
        if(!p) throw Error("Transform unavailable: "+name);
        if(p.isSeparationLeader && p.dimensionsSeparated) throw Error("Separated position is outside this starter");
        return p;
    }
    // Some AE versions return three components even for a 2D layer. Keep the
    // public 2D contract and preserve the host's hidden third component.
    function visibleValue(value,l) {return !l.threeDLayer && value instanceof Array && value.length===3 ? value.slice(0,2) : value;}
    function nativeValue(p,value,l) {var old=p.value;return !l.threeDLayer && value instanceof Array && value.length===2 && old instanceof Array && old.length===3 ? [value[0],value[1],old[2]] : value;}
    function session() {
        if(!app.project) throw Error("Open or create an AE project first");
        var old=$.global.__aeBasicSessionV1, same=false;
        // A project closed since the last call leaves an invalid DOM object; comparing it throws.
        try {same=!!old && old.project === app.project;} catch(stale) {}
        if(!same) {
            old={project:app.project, token:String(new Date().getTime())+"-"+String(Math.random())};
            $.global.__aeBasicSessionV1=old;
        }
        return old.token;
    }
    function snapshot() {
        var s={session:session(), project_file:app.project.file ? app.project.file.fsName : null, project_items:app.project.numItems, active_comp:null, layers:[]};
        var c=app.project.activeItem;
        if(c instanceof CompItem) {
            if(c.numLayers>200) throw Error("Inspect supports up to 200 layers; select a smaller working composition");
            s.active_comp={id:c.id,name:c.name,width:c.width,height:c.height,fps:c.frameRate,duration:c.duration,time:c.time,background_color:c.bgColor};
            for(var i=1;i<=c.numLayers;i++) {
                var l=c.layer(i), row={id:l.id,index:i,name:l.name,three_d:!!l.threeDLayer,locked:l.locked,selected:l.selected,enabled:l.enabled,parent_id:l.parent?l.parent.id:null,animated:[],expressions:[],values:{},key_counts:{}};
                for(var name in matches) if(matches.hasOwnProperty(name)) {
                    try {var p=prop(l,name);row.values[name]=visibleValue(p.value,l);row.key_counts[name]=p.numKeys;if(p.numKeys)row.animated.push(name);if(p.expressionEnabled)row.expressions.push(name);} catch(ignore) {}
                }
                s.layers.push(row);
            }
        }
        s.signature=hash(encode(s));
        return s;
    }
    function comp(target) {
        var c=(typeof target==="string") ? refs[target.substring(1)] : app.project.itemByID(target);
        if(!(c instanceof CompItem)) throw Error("Composition target is missing");
        return c;
    }
    function layer(c, target) {
        var l=null;
        if(typeof target==="string") l=refs[target.substring(1)];
        else for(var i=1;i<=c.numLayers;i++) if(c.layer(i).id===target) {l=c.layer(i);break;}
        if(!l || l.containingComp.id!==c.id || l.locked) throw Error("Layer missing, locked or in another composition");
        if(l instanceof CameraLayer || l instanceof LightLayer) throw Error("Camera/light transforms are outside this starter");
        return l;
    }
    function checkValue(p, v, l) {
        var current=visibleValue(p.value,l);
        if(current instanceof Array) {if(!(v instanceof Array) || v.length!==current.length) throw Error("Transform dimension changed");}
        else if(typeof v!=="number") throw Error("Expected scalar transform");
        if(p.expressionEnabled) throw Error("Existing expression will not be replaced");
    }
    function execute(a) {
        var c,l,p,k,name,changed={},r={op:a.op};
        if(a.op==="create_comp") {
            c=app.project.items.addComp(a.name,a.width,a.height,1,a.duration,a.fps);
            c.openInViewer();
            if(a.ref)refs[a.ref]=c;r.comp_id=c.id;r.name=c.name;r.width=c.width;r.height=c.height;r.fps=c.frameRate;r.duration=c.duration;
        } else if(a.op==="set_comp") {
            c=comp(a.comp);c.bgColor=a.changes.background_color;r.comp_id=c.id;r.background_color=c.bgColor;
        } else if(a.op==="add_null" || a.op==="add_text" || a.op==="add_solid") {
            c=comp(a.comp);
            if(a.op==="add_null") {l=c.layers.addNull();l.threeDLayer=!!a.three_d;}
            else if(a.op==="add_solid") {
                if(c.width!==a.width || c.height!==a.height || Math.abs(c.duration-a.duration)>0.0001)
                    throw Error("Composition dimensions or duration changed");
                l=c.layers.addSolid(a.color,a.name,a.width,a.height,c.pixelAspect,a.duration);
                l.startTime=0;l.inPoint=0;l.outPoint=c.duration;
            }
            else {
                l=c.layers.addText(a.text);
                p=l.property("ADBE Text Properties").property("ADBE Text Document");var d=p.value;
                if(a.font_size!==undefined)d.fontSize=a.font_size;
                if(a.color!==undefined){d.applyFill=true;d.fillColor=a.color;}
                p.setValue(d);
            }
            l.name=a.name;if(a.ref)refs[a.ref]=l;r.comp_id=c.id;r.layer_id=l.id;r.name=l.name;r.three_d=l.threeDLayer;
            if(a.op==="add_text"){var td=l.property("ADBE Text Properties").property("ADBE Text Document").value;r.text=td.text;r.font_size=td.fontSize;r.color=td.fillColor;}
            if(a.op==="add_solid"){r.color=l.source.mainSource.color;r.width=l.source.width;r.height=l.source.height;r.duration=l.outPoint-l.inPoint;}
        } else {
            c=comp(a.comp);l=layer(c,a.layer);r.comp_id=c.id;r.layer_id=l.id;
            if(a.op==="set_layer") {
                if(a.changes.name!==undefined)l.name=a.changes.name;
                if(a.changes.enabled!==undefined)l.enabled=a.changes.enabled;
                r.name=l.name;r.enabled=l.enabled;
            } else if(a.op==="set_transform") {
                for(name in a.values)if(a.values.hasOwnProperty(name)){p=prop(l,name);checkValue(p,a.values[name],l);if(p.numKeys)throw Error("Existing animation: use explicit keyframes");}
                for(name in a.values)if(a.values.hasOwnProperty(name)){p=prop(l,name);p.setValue(nativeValue(p,a.values[name],l));changed[name]=visibleValue(p.value,l);}
                r.values=changed;
            } else if(a.op==="set_keyframes") {
                p=prop(l,a.property);for(k=0;k<a.keys.length;k++)checkValue(p,a.keys[k].value,l);
                var interpolation=a.interpolation==="hold"?KeyframeInterpolationType.HOLD:KeyframeInterpolationType.LINEAR;
                if(!p.isInterpolationTypeValid(interpolation))throw Error("Interpolation unavailable");
                r.property=a.property;r.keys=[];var allInterpolation=true;
                for(k=0;k<a.keys.length;k++) {
                    p.setValueAtTime(a.keys[k].time,nativeValue(p,a.keys[k].value,l));
                    var idx=p.nearestKeyIndex(a.keys[k].time);p.setInterpolationTypeAtKey(idx,interpolation,interpolation);
                    r.keys.push({time:p.keyTime(idx),value:visibleValue(p.keyValue(idx),l)});
                    if(p.keyInInterpolationType(idx)!==interpolation || p.keyOutInterpolationType(idx)!==interpolation)allInterpolation=false;
                }
                r.interpolation=allInterpolation?(a.interpolation||"linear"):"mismatch";
            } else throw Error("Unknown operation");
        }
        return r;
    }
    try {
        if(parseFloat(app.version)<24)throw Error("This starter targets AE24+");
        if(job.schema!=="ae-basic.v1")throw Error("Registry version mismatch");
        if(resultFile.exists || startedFile.exists)throw Error("Already started: read this job receipt and prepare a new job only after inspection");
        var before=snapshot();
        if(!job.inspect_only && (!job.guard || before.session!==job.guard.session || before.signature!==job.guard.signature))throw Error("STALE_SNAPSHOT: project/composition state changed; inspect again");
        write(startedFile,{job_id:job.job_id,started_utc:new Date().toUTCString()});
        if(!job.inspect_only) {
            app.beginUndoGroup("AE Basic "+job.job_id.substring(0,8));undo=true;
            for(var i=0;i<job.actions.length;i++){report.may_have_changes=true;report.actions.push(execute(job.actions[i]));}
        }
        report.status="ok";report.snapshot=snapshot();
    } catch(error) {
        report.status=report.may_have_changes?"partial":"failed";report.error=String(error);report.failed_action_index=report.actions.length;
    } finally {
        if(undo)app.endUndoGroup();
    }
    try {
        // Existing receipts are never overwritten by a second execution.
        if(resultFile.exists)throw Error("Existing receipt preserved; duplicate execution refused");
        write(resultFile,report);
        if(job.notify)alert("AE_BASIC "+report.status.toUpperCase()+" | "+report.actions.length+" actions\n"+resultFile.fsName+(report.error?"\n"+report.error:""));
    } catch(receiptError) {throw Error("AE_BASIC receipt unavailable: "+String(receiptError));}
    return encode(report);
})();
