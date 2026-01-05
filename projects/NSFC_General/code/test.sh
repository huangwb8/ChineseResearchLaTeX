# STAR alignment
STAR \
	--runThreadN ${nthread} \
	--genomeDir ${index_base} \
	--readFilesIn ${fq1} ${fq2} \
	--readFilesCommand  zcat \
	--sjdbGTFfile ${path_gtf} \
	--sjdbOverhang ${sjdbOverhang} \
	--outSAMattrRGline ID:${case} SM:${case} \
	LB:${seq_type} PL:Illumina \
	--outFileNamePrefix ${path_align}/${case}. \
	--outSAMtype BAM SortedByCoordinate \
	--twopassMode Basic \
	> $path_log/STAR_hg38_paired_${case}.log
	
# featureCounts	
featureCounts -T $nthread -p \
	-a $path_genome_gtf \
	--tmpDir /data/ \
	--verbose \
	-t exon -g gene_id  \
	-o $path_count/${case}.count \
	$path_align/${id} \
	> $path_log/featureCounts_${case}.log	