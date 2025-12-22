import pyfastx

fasta_file = "/Users/forrest/GitHub/rustkmer/examples/application/Chr10_demo.fa"
fastx_obj = pyfastx.Fasta(fasta_file)

#print(fastx_obj[-1])
print(pyfastx.__version__)
print(len(fastx_obj))

for seq in fastx_obj:
    print(seq.name)
    print(seq.seq)
    break