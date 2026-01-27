import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

#Load NHANES 2021-2022 data files
demo = pd.read_sas('DEMO_L.XPT')
tchol = pd.read_sas('TCHOL_L.XPT')

#Merge and filter data
df = pd.merge(demo, tchol, on='SEQN')
df_filtered = df[(df['RIAGENDR'] == 1) & 
                 (df['RIDAGEYR'] >= 40) & 
                 (df['RIDAGEYR'] <= 60)]
cholesterol_data = df_filtered['LBXTC'].dropna()

#Create distribution
bins = np.arange(50, 405, 5)
counts, bin_edges = np.histogram(cholesterol_data, bins=bins)
population_perc = (counts / counts.sum()) * 100

# Save CSV
result_df = pd.DataFrame({
    'cholesterol_level': bins[:-1],
    'population_perc': np.round(population_perc, 4)
})
result_df.to_csv('cholesterol_distribution.csv', index=False)

# Create plot
fig, ax = plt.subplots(figsize=(12, 6))
ax.bar(bins[:-1], population_perc, width=4, color='steelblue', edgecolor='darkblue', alpha=0.7)

# Arrow at 184
idx = np.argmin(np.abs(bins[:-1] - 184))
ax.annotate('184 mg/dL', 
            xy=(184, population_perc[idx]),  
            xytext=(220, population_perc[idx] + 2), 
            fontsize=12, 
            fontweight='bold', 
            ha='center',
            arrowprops=dict(arrowstyle='->', color='red', lw=2))

ax.set_xlabel('Total Cholesterol Level (mg/dL)', fontsize=12)
ax.set_ylabel('Percentage of Individuals (%)', fontsize=12)
ax.set_title('Total Cholesterol Distribution\nUS Males Aged 40-60 (NHANES 2021-2022)', fontsize=14, fontweight='bold')
ax.set_xlim(50, 400)
ax.set_xticks(np.arange(50, 401, 50))
ax.grid(axis='y', alpha=0.3)

plt.tight_layout()
plt.savefig('cholesterol_distribution.png', dpi=150, bbox_inches='tight')
plt.show()

print("Done! Files created:")
print("- cholesterol_distribution.csv")
print("- cholesterol_distribution.png")