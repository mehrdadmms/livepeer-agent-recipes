import bpy
sky=[n for n in bpy.context.scene.world.node_tree.nodes if n.type=="TEX_SKY"][0]
base=set(dir(bpy.types.ShaderNode))
print("SKYP",[(p,getattr(sky,p)) for p in ("sun_elevation","sun_rotation","sun_disc","sun_size","sun_intensity","ozone_density","sky_type","sun_direction")if hasattr(sky,p)])
