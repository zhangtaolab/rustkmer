#!/usr/bin/env python3
"""
RustKmer BioPython Integration Examples

This script demonstrates integration with BioPython:
- Working with Bio.Seq objects
- Processing FASTA/FASTQ files
- K-mer analysis of genomic sequences
- Sequence similarity and comparison
- Transcriptomic analysis workflows
"""

from rustkmer import Database, KmerCounter
from Bio import SeqIO
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord
from Bio.SeqFeature import SeqFeature, FeatureLocation
from Bio.SeqUtils.ProtParam import ProteinAnalysis
import tempfile
import os
import sys
import time
import matplotlib.pyplot as plt
import pandas as pd
from collections import Counter, defaultdict
import seaborn as sns

def example_1_basic_biopython_integration():
    """Example 1: Basic BioPython integration."""
    print("=" * 60)
    print("Example 1: Basic BioPython Integration")
    print("=" * 60)

    try:
        # Create sample sequences as Bio.Seq objects
        sequences = [
            Seq("ATCGATCGATCGATCGATCGATCGATCGATCGATCG"),
            Seq("GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAG"),
            Seq("TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT"),
            Seq("CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC"),
            Seq("ATCGATCGATCGATCGATCGATCGATCGATCGATGG"),  # 1 mutation
        ]

        # Create SeqRecord objects with metadata
        records = []
        for i, seq in enumerate(sequences):
            record = SeqRecord(
                seq,
                id=f"seq_{i+1}",
                description=f"Sample sequence {i+1}",
                annotations={"organism": "test", "molecule_type": "DNA"}
            )
            records.append(record)

        print(f"Created {len(records)} BioPython SeqRecord objects:")
        for record in records:
            print(f"  {record.id}: {len(record.seq)} bp, {record.description}")

        # Save sequences as FASTA using BioPython
        with tempfile.NamedTemporaryFile(mode='w', suffix='.fasta', delete=False) as f:
            SeqIO.write(records, f, "fasta")
            fasta_file = f.name

        print(f"\nSaved to FASTA file: {fasta_file}")

        # Create k-mer database using RustKmer
        print("\nCreating k-mer database...")
        kmer_size = 31
        counter = KmerCounter(k=kmer_size, canonical=True)
        counter.count_file(fasta_file)

        # Save database
        db_path = "biopython_example.rkdb"
        counter.save_to_database(db_path)
        print(f"Database saved to: {db_path}")

        # Query database with BioPython sequences
        print("\nQuerying database with BioPython sequences...")
        with Database(db_path) as db:
            for record in records:
                kmer = str(record.seq[:kmer_size]) if len(record.seq) >= kmer_size else str(record.seq)
                result = db.query(kmer)
                print(f"  {record.id}: {result.is_present} (count: {result.count:,})")

        # Clean up
        os.unlink(fasta_file)
        os.unlink(db_path)

    except Exception as e:
        print(f"Error: {e}")
        return False

    return True


def example_2_sequence_similarity_analysis():
    """Example 2: Sequence similarity analysis using k-mers."""
    print("\n" + "=" * 60)
    print("Example 2: Sequence Similarity Analysis")
    print("=" * 60)

    try:
        # Create test sequences with varying similarity
        sequences_data = [
            ("gene_A", "ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCG"),
            ("gene_B", "ATCGATCGATCGATCGATCGATCGATCGATCGATGGATCGATCGATCGATCG"),  # 2 mutations
            ("gene_C", "GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAG"),  # Distant
            ("gene_D", "ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCG"),  # Same as A
            ("gene_E", "ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATGG"),  # 1 mutation
        ]

        # Create BioPython records
        records = []
        for seq_id, sequence in sequences_data:
            record = SeqRecord(
                Seq(sequence),
                id=seq_id,
                description=f"Test sequence for similarity analysis",
                features=[
                    SeqFeature(
                        FeatureLocation(0, len(sequence)),
                        type="source",
                        qualifiers={"note": f"Synthetic sequence {seq_id}"}
                    )
                ]
            )
            records.append(record)

        # Create database
        with tempfile.NamedTemporaryFile(mode='w', suffix='.fasta', delete=False) as f:
            SeqIO.write(records, f, "fasta")
            fasta_file = f.name

        kmer_size = 31
        counter = KmerCounter(k=kmer_size, canonical=True)
        counter.count_file(fasta_file)
        db_path = "similarity_analysis.rkdb"
        counter.save_to_database(db_path)

        # Perform pairwise similarity analysis
        print("Performing pairwise similarity analysis...")
        similarity_matrix = {}

        with Database(db_path) as db:
            for i, record1 in enumerate(records):
                similarity_matrix[record1.id] = {}
                sequence1 = str(record1.seq)

                if len(sequence1) < kmer_size:
                    print(f"  Skipping {record1.id} (sequence too short)")
                    continue

                query_kmer = sequence1[:kmer_size]
                result1 = db.query(query_kmer)

                for j, record2 in enumerate(records):
                    if i <= j:  # Only compute upper triangle
                        continue

                    sequence2 = str(record2.seq)
                    if len(sequence2) < kmer_size:
                        continue

                    query_kmer2 = sequence2[:kmer_size]
                    result2 = db.query(query_kmer2)

                    # Calculate similarity based on shared k-mers
                    total_kmers = result1.count + result2.count - result1.count  # Simplified
                    similarity = result1.count / max(total_kmers, 1)
                    similarity_matrix[record1.id][record2.id] = similarity

        # Display similarity results
        print("\nSimilarity Results:")
        print("-" * 40)
        for seq1, similarities in similarity_matrix.items():
            for seq2, score in similarities.items():
                print(f"  {seq1} vs {seq2}: {score:.4f}")

        # Create similarity visualization
        if similarity_matrix:
            print("\nCreating similarity heatmap...")
            df = pd.DataFrame(similarity_matrix).T
            plt.figure(figsize=(8, 6))
            sns.heatmap(df, annot=True, cmap="YlOrRd", vmin=0, vmax=1)
            plt.title("Sequence Similarity Matrix")
            plt.tight_layout()
            plt.savefig("similarity_heatmap.png", dpi=150, bbox_inches='tight')
            print("Similarity heatmap saved to: similarity_heatmap.png")
            plt.close()

        # Clean up
        os.unlink(fasta_file)
        os.unlink(db_path)

    except Exception as e:
        print(f"Error: {e}")
        return False

    return True


def example_3_transcriptome_analysis():
    """Example 3: Transcriptome analysis with k-mers."""
    print("\n" + "=" * 60)
    print("Example 3: Transcriptome Analysis")
    print("=" * 60)

    try:
        # Create sample transcript sequences (including UTRs and coding regions)
        transcripts = [
            {
                "id": "transcript_1",
                "gene": "GENE1",
                "utr5": "AUGCGUACGUACGUACGUACG",
                "coding": "ATGGCCATTGTAATGGGCCGCTGAAAGGGTGCCCGATAG",
                "utr3": "AAUAAUAAUAAUAAUAAUAAU",
                "expression": 100.0
            },
            {
                "id": "transcript_2",
                "gene": "GENE1",
                "utr5": "AUGCGUACGUACGUACGUACG",
                "coding": "ATGGCCATTGTAATGGGCCGCTGAAAGGGTGCCCGATAG",  # Same as transcript 1
                "utr3": "AAUAAUAAUAAUAAUAAUAAU",
                "expression": 150.0  # Higher expression
            },
            {
                "id": "transcript_3",
                "gene": "GENE2",
                "utr5": "UCGAUCGAUCGAUCGAUCGAU",
                "coding": "ATGCCCTAAATGGATGCCGATGATGGATGATGGATGATGG",
                "utr3": "UUAUUAAUUAAUUAAUUAAUUAA",
                "expression": 75.0
            },
            {
                "id": "transcript_4",
                "gene": "GENE3",
                "utr5": "GCAUGCUGCUGCUGCUGCUGC",
                "coding": "ATGCGATCGATCGATCGATCGATCGATCGATCGATCGA",
                "utr3": "AUAAUUAAUUAAUUAAUUAAUU",
                "expression": 50.0
            }
        ]

        # Create BioPython transcript records
        transcript_records = []
        for transcript in transcripts:
            # Convert RNA to DNA (U -> T)
            full_seq = transcript["utr5"].replace('U', 'T') + \
                       transcript["coding"] + \
                       transcript["utr3"].replace('U', 'T')

            record = SeqRecord(
                Seq(full_seq),
                id=transcript["id"],
                description=f"{transcript['gene']} transcript, expression: {transcript['expression']}",
                annotations={
                    "gene": transcript["gene"],
                    "expression": transcript["expression"],
                    "molecule_type": "mRNA"
                },
                features=[
                    SeqFeature(
                        FeatureLocation(0, len(transcript["utr5"])),
                        type="5'UTR"
                    ),
                    SeqFeature(
                        FeatureLocation(len(transcript["utr5"]),
                                      len(transcript["utr5"]) + len(transcript["coding"])),
                        type="CDS",
                        qualifiers={"gene": transcript["gene"]}
                    ),
                    SeqFeature(
                        FeatureLocation(len(transcript["utr5"]) + len(transcript["coding"]),
                                      len(full_seq)),
                        type="3'UTR"
                    )
                ]
            )
            transcript_records.append(record)

        # Save transcripts
        with tempfile.NamedTemporaryFile(mode='w', suffix='.fasta', delete=False) as f:
            SeqIO.write(transcript_records, f, "fasta")
            fasta_file = f.name

        # Create transcriptome database
        print("Creating transcriptome database...")
        kmer_size = 25  # Smaller k for transcripts
        counter = KmerCounter(k=kmer_size, canonical=True)
        counter.count_file(fasta_file)
        db_path = "transcriptome.rkdb"
        counter.save_to_database(db_path)

        # Analyze transcript expression via k-mer abundance
        print("\nAnalyzing transcript expression via k-mer abundance...")
        expression_analysis = {}

        with Database(db_path) as db:
            for record in transcript_records:
                # Extract k-mers from coding region only
                cds_feature = [f for f in record.features if f.type == "CDS"][0]
                cds_seq = str(record.seq[cds_feature.location.start:cds_feature.location.end])

                if len(cds_seq) >= kmer_size:
                    # Sample k-mers from coding region
                    kmer_count = 0
                    total_count = 0

                    for i in range(0, len(cds_seq) - kmer_size + 1, kmer_size):
                        kmer = cds_seq[i:i+kmer_size]
                        result = db.query(kmer)
                        if result.is_present:
                            kmer_count += 1
                            total_count += result.count

                    avg_count = total_count / max(kmer_count, 1)
                    expression_analysis[record.id] = {
                        "gene": record.annotations["gene"],
                        "expected_expression": record.annotations["expression"],
                        "estimated_expression": avg_count,
                        "kmers_found": kmer_count,
                        "total_kmers": len(cds_seq) // kmer_size
                    }

        # Compare expected vs estimated expression
        print("\nExpression Analysis Results:")
        print("-" * 70)
        print(f"{'Transcript':<12} {'Gene':<8} {'Expected':<10} {'Estimated':<10} {'Kmers':<8}")
        print("-" * 70)

        for transcript_id, data in expression_analysis.items():
            print(f"{transcript_id:<12} {data['gene']:<8} "
                  f"{data['expected_expression']:<10.1f} "
                  f"{data['estimated_expression']:<10.1f} "
                  f"{data['kmers_found']:<8}")

        # Create expression correlation plot
        if expression_analysis:
            print("\nCreating expression correlation plot...")
            expected = [data["expected_expression"] for data in expression_analysis.values()]
            estimated = [data["estimated_expression"] for data in expression_analysis.values()]

            plt.figure(figsize=(8, 6))
            plt.scatter(expected, estimated, alpha=0.7, s=100)
            plt.plot([0, max(expected)], [0, max(expected)], 'r--', label='1:1 correlation')
            plt.xlabel("Expected Expression")
            plt.ylabel("Estimated Expression (k-mer abundance)")
            plt.title("Expression Correlation Analysis")
            plt.legend()
            plt.grid(True, alpha=0.3)
            plt.savefig("expression_correlation.png", dpi=150, bbox_inches='tight')
            print("Expression correlation plot saved to: expression_correlation.png")
            plt.close()

        # Clean up
        os.unlink(fasta_file)
        os.unlink(db_path)

    except Exception as e:
        print(f"Error: {e}")
        return False

    return True


def example_4_metagenomics_profiling():
    """Example 4: Metagenomics profiling with k-mers."""
    print("\n" + "=" * 60)
    print("Example 4: Metagenomics Profiling")
    print("=" * 60)

    try:
        # Create sample metagenomic sequences from different "organisms"
        metagenomic_data = {
            "bacteria_1": [
                "ATGCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCG",
                "GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAG",
                "TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT"
            ],
            "bacteria_2": [
                "CCGGAATTCCGGAATTCCGGAATTCCGGAATTCCGGAATTCCGGA",
                "AAGGTTCCGGAAAGGTTCCGGAAAGGTTCCGGAAAGGTTCCGGAAA",
                "GGCCCCGGGGCCCCGGGGCCCCGGGGCCCCGGGGCCCCGGGGCCC"
            ],
            "archaea": [
                "TATATATATATATATATATATATATATATATATATATATATATAT",
                "GCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGC",
                "AAAAATTTTTAAAAATTTTTAAAAATTTTTAAAAATTTTTAAAAA"
            ],
            "virus": [
                "ATATATATATATATATATATATATATATATATATATATATATAT",
                "CGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGC",
                "TATATATATATATATATATATATATATATATATATATATATAT"
            ]
        }

        # Create BioPython records for metagenomic samples
        all_records = []
        for organism, sequences in metagenomic_data.items():
            for i, seq in enumerate(sequences):
                record = SeqRecord(
                    Seq(seq),
                    id=f"{organism}_{i+1}",
                    description=f"Metagenomic sequence from {organism}",
                    annotations={
                        "organism": organism,
                        "domain": organism.split('_')[0],
                        "sample_id": f"sample_{len(all_records)+1}"
                    }
                )
                all_records.append(record)

        # Create comprehensive metagenome database
        print("Creating metagenome database...")
        with tempfile.NamedTemporaryFile(mode='w', suffix='.fasta', delete=False) as f:
            SeqIO.write(all_records, f, "fasta")
            fasta_file = f.name

        kmer_size = 21
        counter = KmerCounter(k=kmer_size, canonical=True)
        counter.count_file(fasta_file)
        db_path = "metagenome.rkdb"
        counter.save_to_database(db_path)

        # Create organism-specific k-mer profiles
        print("\nCreating organism-specific k-mer profiles...")
        organism_profiles = {}

        for organism in metagenomic_data.keys():
            print(f"  Profiling {organism}...")
            organism_kmers = set()

            for seq in metagenomic_data[organism]:
                if len(seq) >= kmer_size:
                    for i in range(len(seq) - kmer_size + 1):
                        kmer = seq[i:i+kmer_size]
                        organism_kmers.add(kmer)

            organism_profiles[organism] = organism_kmers
            print(f"    Found {len(organism_kmers)} unique k-mers")

        # Profile unknown environmental sample
        print("\nProfiling environmental sample...")
        environmental_seqs = [
            "ATGCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCG",  # bacteria_1
            "CCGGAATTCCGGAATTCCGGAATTCCGGAATTCCGGAATTCCGGA",  # bacteria_2
            "TATATATATATATATATATATATATATATATATATATATATATAT",  # archaea
            "ATATATATATATATATATATATATATATATATATATATATATATAT",  # virus
        ]

        sample_kmers = set()
        for seq in environmental_seqs:
            if len(seq) >= kmer_size:
                for i in range(len(seq) - kmer_size + 1):
                    kmer = seq[i:i+kmer_size]
                    sample_kmers.add(kmer)

        # Calculate composition
        print("\nEnvironmental Sample Composition:")
        print("-" * 50)

        composition = {}
        total_matches = 0

        with Database(db_path) as db:
            for organism, profile_kmers in organism_profiles.items():
                matches = 0
                for kmer in sample_kmers:
                    if kmer in profile_kmers:
                        result = db.query(kmer)
                        if result.is_present:
                            matches += 1

                total_matches += matches
                composition[organism] = matches
                print(f"  {organism}: {matches} k-mer matches")

        if total_matches > 0:
            print(f"\nRelative Abundance:")
            for organism, matches in composition.items():
                percentage = matches / total_matches * 100
                print(f"  {organism}: {percentage:.1f}%")

        # Create composition visualization
        if composition and total_matches > 0:
            print("\nCreating composition pie chart...")
            plt.figure(figsize=(8, 8))
            labels = list(composition.keys())
            sizes = [count / total_matches * 100 for count in composition.values()]

            plt.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90)
            plt.title("Environmental Sample Composition")
            plt.axis('equal')
            plt.savefig("metagenome_composition.png", dpi=150, bbox_inches='tight')
            print("Composition chart saved to: metagenome_composition.png")
            plt.close()

        # Clean up
        os.unlink(fasta_file)
        os.unlink(db_path)

    except Exception as e:
        print(f"Error: {e}")
        return False

    return True


def example_5_protein_domain_analysis():
    """Example 5: Protein domain analysis using k-mers."""
    print("\n" + "=" * 60)
    print("Example 5: Protein Domain Analysis")
    print("=" * 60)

    try:
        # Create protein sequences with known domains
        proteins = {
            "kinase_domain": "MAGVVVDPTVGTLSKGQLGFLENRLRHVNVREFLTNFRMELVNDA",
            "zinc_finger": "MTSYKDVQRRNGISQPPRAGFVPNDGYDVVHTKGKVSEKGNIRKVR",
            "transmembrane": "MGNLLLLLLLLLLVATAAAAVAAAASSSSSSDDDDDDDEEEEE",
            "dna_binding": "MPRGKGKGFKGSNKGKGGLGKGGKGKGSKGSFKATKAVNFKLGNV",
            "enzyme_active": "AVHRLAGAGLSVVVVAGAGTSALAALAAAVATVPAPVAAAGAS",
        }

        # Create BioPython protein records
        protein_records = []
        for domain, sequence in proteins.items():
            record = SeqRecord(
                Seq(sequence),
                id=f"protein_{domain}",
                description=f"Protein containing {domain.replace('_', ' ')}",
                annotations={
                    "domain_type": domain,
                    "protein_type": "enzyme" if "enzyme" in domain else "structural",
                    "length": len(sequence)
                },
                features=[
                    SeqFeature(
                        FeatureLocation(0, len(sequence)),
                        type="domain",
                        qualifiers={"note": domain.replace('_', ' ')}
                    )
                ]
            )
            protein_records.append(record)

        # Translate proteins back to DNA for k-mer analysis
        # (simulating the original coding sequences)
        dna_records = []
        for record in protein_records:
            # Simplified reverse translation (codon usage not optimized)
            codon_table = {
                'A': 'GCT', 'R': 'CGT', 'N': 'AAT', 'D': 'GAT', 'C': 'TGT',
                'Q': 'CAA', 'E': 'GAA', 'G': 'GGT', 'H': 'CAT', 'I': 'ATT',
                'L': 'CTT', 'K': 'AAA', 'M': 'ATG', 'F': 'TTT', 'P': 'CCT',
                'S': 'TCT', 'T': 'ACT', 'W': 'TGG', 'Y': 'TAT', 'V': 'GTT',
                'X': 'NNN'  # Unknown amino acid
            }

            dna_seq = ""
            for aa in str(record.seq):
                dna_seq += codon_table.get(aa, 'NNN')

            dna_record = SeqRecord(
                Seq(dna_seq),
                id=record.id + "_dna",
                description=record.description + " (coding sequence)",
                annotations=record.annotations
            )
            dna_records.append(dna_record)

        # Create database from coding sequences
        print("Creating protein domain database...")
        with tempfile.NamedTemporaryFile(mode='w', suffix='.fasta', delete=False) as f:
            SeqIO.write(dna_records, f, "fasta")
            fasta_file = f.name

        kmer_size = 15  # Smaller k for proteins
        counter = KmerCounter(k=kmer_size, canonical=True)
        counter.count_file(fasta_file)
        db_path = "protein_domains.rkdb"
        counter.save_to_database(db_path)

        # Analyze domain-specific k-mers
        print("\nAnalyzing domain-specific k-mer patterns...")
        domain_signatures = {}

        with Database(db_path) as db:
            for i, record in enumerate(dna_records):
                domain_type = record.annotations["domain_type"]
                dna_seq = str(record.seq)

                # Sample k-mers across the protein
                signature_kmers = []
                for j in range(0, len(dna_seq) - kmer_size + 1, kmer_size):
                    kmer = dna_seq[j:j+kmer_size]
                    result = db.query(kmer)
                    if result.is_present and result.count > 0:
                        signature_kmers.append((kmer, result.count))

                # Sort by abundance and keep top signatures
                signature_kmers.sort(key=lambda x: x[1], reverse=True)
                domain_signatures[domain_type] = signature_kmers[:5]  # Top 5 signatures

                print(f"\n  {domain_type.replace('_', ' ').title()} Domain:")
                print(f"    Protein length: {len(record.seq) // 3} aa")
                print(f"    Coding sequence: {len(dna_seq)} bp")
                print(f"    Signature k-mers (top 5):")
                for kmer, count in signature_kmers[:5]:
                    print(f"      {kmer[:10]}...: {count:,} occurrences")

        # Test domain detection in unknown sequence
        print("\nTesting domain detection in unknown protein...")
        unknown_protein = "MAGVVVDPTVGTLSKGQLGFLENRLRHVNVREFLTNFRMELVNDA"  # kinase domain
        unknown_dna = ""
        codon_table = {
            'A': 'GCT', 'R': 'CGT', 'N': 'AAT', 'D': 'GAT', 'C': 'TGT',
            'Q': 'CAA', 'E': 'GAA', 'G': 'GGT', 'H': 'CAT', 'I': 'ATT',
            'L': 'CTT', 'K': 'AAA', 'M': 'ATG', 'F': 'TTT', 'P': 'CCT',
            'S': 'TCT', 'T': 'ACT', 'W': 'TGG', 'Y': 'TAT', 'V': 'GTT'
        }

        for aa in unknown_protein:
            unknown_dna += codon_table.get(aa, 'NNN')

        # Check for domain matches
        with Database(db_path) as db:
            domain_matches = defaultdict(int)
            total_matches = 0

            for j in range(0, len(unknown_dna) - kmer_size + 1, kmer_size):
                kmer = unknown_dna[j:j+kmer_size]
                result = db.query(kmer)
                if result.is_present:
                    total_matches += result.count

                    # Check which domains contain this k-mer
                    for domain, signatures in domain_signatures.items():
                        for sig_kmer, sig_count in signatures:
                            if kmer == sig_kmer:
                                domain_matches[domain] += sig_count

        print("\nDomain Detection Results:")
        print("-" * 40)
        if total_matches > 0:
            for domain, matches in sorted(domain_matches.items(),
                                        key=lambda x: x[1], reverse=True):
                percentage = matches / total_matches * 100
                print(f"  {domain.replace('_', ' ').title()}: {percentage:.1f}% "
                      f"({matches:,} k-mer matches)")
        else:
            print("  No domain matches found")

        # Clean up
        os.unlink(fasta_file)
        os.unlink(db_path)

    except Exception as e:
        print(f"Error: {e}")
        return False

    return True


def main():
    """Run all BioPython integration examples."""
    print("RustKmer BioPython Integration Examples")
    print("========================================")

    examples = [
        ("Basic BioPython Integration", example_1_basic_biopython_integration),
        ("Sequence Similarity Analysis", example_2_sequence_similarity_analysis),
        ("Transcriptome Analysis", example_3_transcriptome_analysis),
        ("Metagenomics Profiling", example_4_metagenomics_profiling),
        ("Protein Domain Analysis", example_5_protein_domain_analysis)
    ]

    results = []
    for name, example_func in examples:
        print(f"\nRunning: {name}")
        try:
            success = example_func()
            results.append((name, success))
        except Exception as e:
            print(f"Example '{name}' failed with error: {e}")
            results.append((name, False))

    # Summary
    print("\n" + "=" * 60)
    print("EXAMPLES SUMMARY")
    print("=" * 60)

    for name, success in results:
        status = "✓ PASSED" if success else "✗ FAILED"
        print(f"{name:30} {status}")

    passed = sum(1 for _, success in results if success)
    total = len(results)

    print(f"\nTotal: {passed}/{total} examples completed successfully")

    if passed == total:
        print("🎉 All BioPython integration examples completed successfully!")
        return 0
    else:
        print("⚠️  Some examples failed. Check the output above for details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())