# usage: blender -b -P blender/prep_model.py -- in.glb out.glb ratio
import bpy,sys
a=sys.argv[sys.argv.index('--')+1:]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=a[0])
for o in list(bpy.data.objects):
    if o.type=='MESH':
        m=o.modifiers.new('d','DECIMATE'); m.ratio=float(a[2])
        bpy.context.view_layer.objects.active=o
        bpy.ops.object.modifier_apply(modifier='d')
        print(o.name,len(o.data.polygons))
bpy.ops.export_scene.gltf(filepath=a[1],export_format='GLB')
