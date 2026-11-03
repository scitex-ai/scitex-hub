from pathlib import Path
import argparse
import json
import matplotlib
matplotlib.use('Agg')
import figrecipe as fr
parser=argparse.ArgumentParser(description='Create synthetic FigRecipe landing examples; never research results.')
parser.add_argument('output_directory',type=Path,help='New directory to create; an existing path is refused')
root=parser.parse_args().output_directory.resolve()
root.mkdir(parents=True,exist_ok=False)
outputs=[]
for name in ['01_synthetic_learning_curve','02_synthetic_group_comparison','03_synthetic_response_curve']:
 fig,ax=fr.subplots(figsize=(6,4))
 if name.startswith('01'):
  ax.plot([1,2,3,4,5,6,7,8],[.52,.64,.72,.78,.82,.85,.87,.88],label='Training',color='#008c95')
  ax.plot([1,2,3,4,5,6,7,8],[.5,.61,.69,.74,.77,.79,.8,.81],label='Validation',color='#dd8452')
  ax.set_xlabel('Epoch');ax.set_ylabel('Accuracy');ax.set_ylim(.4,1);ax.legend();ax.set_title('Synthetic learning curves')
 elif name.startswith('02'):
  ax.bar(['Baseline','Model A','Model B'],[.68,.81,.86],color=['#888888','#008c95','#dd8452']);ax.set_ylabel('Illustrative score');ax.set_ylim(0,1);ax.set_title('Synthetic group comparison')
 else:
  ax.plot([0,1,2,3,4,5],[.1,.2,.45,.7,.83,.9],color='#008c95',marker='o');ax.set_xlabel('Dose (arbitrary units)');ax.set_ylabel('Illustrative response');ax.set_title('Synthetic response curve')
 fr.save(fig,root/(name+'.png'),validate=False,verbose=False)
 outputs.append({'recipe':name+'.yaml','existing':False})
(root/'README-EXAMPLE.txt').write_text('Synthetic interface demonstration only. These curves and values are invented and are not MNIST experimental results. Created2026-11-03 for the FigRecipe landing screenshot. Existing user files were not modified.\n')
print(json.dumps({'root':str(root),'outputs':outputs}))
