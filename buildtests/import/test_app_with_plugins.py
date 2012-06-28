
#
# this little sample application generates a plugin on the fly, and then tries to import it.
#
import os,sys

# 
# we first import a static plugin; the application might have certain plugins that it always loads.
#
mdl = __import__("static_plugin")


plugin_contents = """
print("DYNAMIC PLUGIN IMPORTED.")
print("This is some user-generated plugin that does not come into existence util after the application starts,")
print("  and other modules in the directory it will reside in happen to have been imported (like the static_plugin)")
"""

#
# create the dynamic plugin in the same directory as the executable.
#
program_dir = os.path.abspath(sys.path[0])
plugin_filename = os.path.join(program_dir,"dynamic_plugin.py")
fp = open(plugin_filename,"w")
fp.write(plugin_contents)
fp.close()

try:
   print("Attempting to import dynamic_plugin...") 
   mdl = __import__("dynamic_plugin")
   sys.exit(0)
except Exception as e:
   print("Failed to import the dynamic plugin.")
   sys.exit(1)
finally:
   # 
   # clean up.     
   #
   try:             os.remove(plugin_filename)
   except OSError: pass
   try:             os.remove(plugin_filename+"c")
   except OSError: pass

