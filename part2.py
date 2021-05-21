import pandas as pd
dataset = pd.read_csv('Student_marks_list.csv')

'''
PART 1

'''

# for each column except 'Name', get the index of max value using idxmax()
maxIndex=dataset.iloc[:,1:].idxmax()

# Iterate through all key-value pairs in the series maxIndex and print the answer accordingly
for subject, student in zip(maxIndex.keys(), maxIndex.values):
    print('Topper in {sub} is {stu}'.format(sub=subject, stu=dataset.iloc[student, 0]))

# Time complexity analysis

# Time complexity of idxmax() is O(m*n) where m is the no.of columns and n is the no.of records/rows. 
# Since m is very small (6 in this case), time complexity can be represented as O(n). 

print('\n\n')

'''
PART 2

'''

# def returnSum(record):
#     return sum(record[1:])

dataset['total'] = dataset.apply(lambda x: sum(x[1:]), axis=1)
top3 = dataset.nlargest(3, 'total')['Name'].values
print('The three best students are {a}, {b}, {c}'.format(a=top3[0], b=top3[1], c=top3[2]))
# Time complexity analysis

# Time complexity: O(nlogn) due to sorting.