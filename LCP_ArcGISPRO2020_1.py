"""python script developed for use with ArcGIS Pro installations (python 3.xx).  Script performs least cost path
    analysis for all pairwise combinations of locations in feature class one and feature class two.  Tool also converts
    least cost path rasters into polylines, and measures the linear distance of those polylines in meters, and saves,
    for each pairwise combination, an excel file containing the names of the two locations, the cost of the least cost
    path between them, in whichever unit the user specified through use of a cost function, and the linear distance of
    the least cost path between them."""

import arcpy
from arcpy.sa import *
from time import *

_author_ = "Ian Jorgeson <ijorgeson@mail.smu.edu>"


######### FUNCTIONS CALLED BY SCRIPT - DO NOT EDIT!!! ##########

# Function that calculates pathdistance raster and backlink raster from digital elevation model (DEM), point class
# shapefile, and vertical factor derived from calorie cost, time cost, or other cost model.
def path_distance(feature_class, dem, vf, file_name_1):
    try:
        out_distance_raster = PathDistance(feature_class, "", dem, "", "", dem, vf, "",
                                           directory + r'\backlink\bl_' + file_name_1)
        out_distance_raster.save(directory + r'\pathdis\pd_' + file_name_1)
        return out_distance_raster
    except arcpy.ExecuteError:
        error = arcpy.GetMessages(2)
        print(str(error))
        log.write(asctime() + ': Failed to generate pathdistance and backlink rasters for  ' + loc_one_name
                  + '.\n' + str(error) +
                  '------------------------------------------------------------------------------------------' + '\n')
    except Exception as error:
        print('Failed to generate pathdistance and backlink rasters for ' + loc_one_name)
        log.write(asctime() + ': Failed to generate pathdistance and backlink rasters for  ' + loc_one_name
                  + '.\n' + str(error) +
                  '------------------------------------------------------------------------------------------' + '\n')

# Function that calculates least cost path from a location in a referenced in a point, line, or polygon class shapefile
# back to the location for which the pathdistance raster was previously calculated.
def cost_path(feature_class, out_distance_raster, back_link):
    try:
        out_cost_path = CostPath(feature_class, out_distance_raster, back_link)
        return out_cost_path
    except arcpy.ExecuteError:
        error = arcpy.GetMessages(2)
        print(str(error))
        log.write(asctime() + ': Failed to calculate least cost path between ' + loc_one_name + ' and '
                  + loc_two_name + '.\n' + str(error) +
                  '------------------------------------------------------------------------------------------' + '\n')
    except Exception as error:
        print('Failed to calculate least cost path between ' + loc_one_name + ' and ' + loc_two_name + '.')
        print('Script will continue with next iteration.  See error message for more details.')
        print(error)
        print('\n')
        log.write(asctime() + ': Something went wrong while working with costpath raster between '
                  + loc_one_name + ' and ' + loc_two_name + '.\n'
                  + 'Script continued with next iteration.  See error message for more details.\n'
                  + str(error) + '\n'
                  + '------------------------------------------------------------------------------------------'
                  + '\n')


# Function that converts resulting least cost path into simplified polyline; calculates length of the resulting
# polyline; and stores that length, names of source and destination locations, and cost of path in table.
def convert(costpath, file_name_1, file_name_2, name_1, name_2):
    try:
        arcpy.RasterToPolyline_conversion(costpath, directory + '\polylines\pl_' + file_name_1 + '_' + file_name_2,
                                          "ZERO", 10, "SIMPLIFY")
        distance = 0
        with arcpy.da.SearchCursor(directory + '\polylines\pl_' + file_name_1 + '_' + file_name_2 + '.shp',
                                   ['SHAPE@LENGTH']) as poly_cursor:
            for row in poly_cursor:
                distance += row[0]  # sum distance for each polyline segment
    except arcpy.ExecuteError:
        error = arcpy.GetMessages(2)
        str_error = str(error)
        if str_error.startswith('ERROR 010151'):
            print('\nCannot convert cost path raster between ' + loc_one_name + ' and ' + loc_two_name +
                  ' to a valid polyline, but rest of data should be saved properly.  Source and destination may be too'
                  'close to each other.')
            print('Linear distance between source and destination set to zero in output table.')
            print(str(error))
            log.write(asctime() + ': Cannot convert cost path raster between ' + loc_one_name + ' and ' + loc_two_name +
                      ' to a valid polyline, but rest of data should be saved properly.\n'
                      + 'Linear distance between source and destination set to zero in output table.\n' + str(error) +
                      '------------------------------------------------------------------------------------------'
                      + '\n')
            distance = 0
        else:
            print('\nCannot convert cost path raster between ' + loc_one_name + ' and ' + loc_two_name +
                  ' to a valid polyline, but rest of data should be saved properly.')
            print('Linear distance between source and destination not calculated.')
            print(str(error))
            log.write(asctime() + ': Cannot convert cost path raster between ' + loc_one_name + ' and ' + loc_two_name +
                      ' to a valid polyline, but rest of data should be saved properly.\n'
                      + 'Linear distance between source and destination not calculated.\n' + str(error) +
                      '------------------------------------------------------------------------------------------'
                      + '\n')
            distance = 'NA'
    except Exception as error:
        print('\nCannot convert cost path raster between ' + loc_one_name + ' and ' + loc_two_name +
              ' to a valid polyline.')
        print('Linear distance between source and destination not calculated.')
        print(str(error))
        log.write(asctime() + ': Cannot convert cost path raster between ' + loc_one_name + ' and ' + loc_two_name +
                  ' to a valid polyline, but rest of data should be saved properly.\n'
                  + 'Linear distance between source and destination not calculated.\n' + str(error) +
                  '------------------------------------------------------------------------------------------'
                  + '\n')
        distance = 0

    try:
        arcpy.AddField_management(costpath, 'Source', 'TEXT')
        arcpy.AddField_management(costpath, 'Dest', 'TEXT')
        arcpy.AddField_management(costpath, 'Distance', 'FLOAT')
        arcpy.CalculateField_management(costpath, 'Source', "'" + name_1 + "'")
        arcpy.CalculateField_management(costpath, 'Dest', "'" + name_2 + "'")
        arcpy.CalculateField_management(costpath, 'Distance', distance)
        arcpy.MakeTableView_management(costpath, 'table')
        with arcpy.da.SearchCursor('table', ['SOURCE', 'DEST', 'PATHCOST',
                                             'DISTANCE', 'STARTROW']) as table_cursor:
            for entry in table_cursor:
                if entry[4] != 0:
                    in_cursor = arcpy.da.InsertCursor(table, fields)
                    in_cursor.insertRow((str(entry[0]), str(entry[1]), entry[2], entry[3]))
                    del in_cursor

        if int_data is True:
            try:
                arcpy.CopyRows_management(costpath, directory + r'\tables\tb_' + file_name_1 + '_' + file_name_2
                                          + '.csv')
            except Exception as error:
                print('\nFailed to save data for cost path between ' + loc_one_name + ' and ' + loc_two_name
                      + ' in .csv table. See error message for more details.')
                print('Linear distance between source and destination not calculated.')
                print(str(error))
                log.write(asctime() + ': Failed to save data for cost path between ' + loc_one_name + ' and '
                          + loc_two_name + ' in .csv table. See error message for more details.\n' + str(error) +
                          '------------------------------------------------------------------------------------------'
                          + '\n')

            try:
                costpath.save(directory + r'\costpath\cp_' + file_name_1 + '_' + file_name_2)
            except Exception as error:
                str_error = str(error)
                if str_error.startswith('ERROR 010240'):
                    print('\nCould not save cost path raster cp_' + file_name_1 + '_'
                          + file_name_2 + ', but rest of data should be saved properly.')
                    print('Combination of file names for fc one and fc two likely exceeds 13 characters. '
                          'See help file for more information.')
                    log.write(asctime() + ': Could not save cost path raster cp_' + file_name_1 + '_'
                              + file_name_2 + ', but rest of data should be saved properly.\n'
                              + 'Combination of file names for fc one and fc two likely exceed 13 characters. '
                                'See help file for more information.\n' + str(error) + '\n'
                              + '----------------------------------------------------'
                                '--------------------------------------'
                              + '\n')
                else:
                    print('\nCould not save cost path raster cp_' + file_name_1 + '_' + file_name_2 +
                          ', but rest of data should be saved properly. See error message for more details')
                    print(str(error))
                    log.write(asctime() + ': Could not save cost path raster cp_' + file_name_1 + '_' + file_name_2 +
                              ', but rest of data should be saved properly. See error message for more details.\n' +
                              '-------------------------------------------------------'
                              '-----------------------------------'
                              + '\n')
    except arcpy.ExecuteError:
        error = arcpy.GetMessages(2)
        print('\nFailed to properly save data for least cost path between ' + loc_one_name + ' and ' + loc_two_name +
              ' in master table. Script will continue with next iteration(1).')
        print(str(error))
        log.write(asctime() + ': Failed to properly save data for least cost path between ' + loc_one_name + ' and '
                  + loc_two_name + ' in master table. Script continued with next iteration.'
                  + '.\n' + str(error) +
                  '------------------------------------------------------------------------------------------' + '\n')
    except Exception as error:
        print('\nFailed to properly save data for least cost path between ' + loc_one_name + ' and ' + loc_two_name +
              ' in master table. Script will continue with next iteration(2).')
        print(str(error))
        log.write(asctime() + ': Failed to properly save data for least cost path between ' + loc_one_name + ' and '
                  + loc_two_name + ' in master table. Script continued with next iteration.'
                  + '.\n' + str(error) +
                  '------------------------------------------------------------------------------------------' + '\n')

########### USER PARAMATERS - EDIT WITH PATHS TO INPUT DATA AND OUTPUT FOLDER############

# Sets environmental parameters. Default is set to overwrite previous files of the same name.  Change to False to
# preserve previously generated files, but note that this will require changing location or name of output files before
# running again.
arcpy.env.overwriteOutput = True
arcpy.env.extent = "MAXOF"

# Notes and stores clock time for start of analysis.
start_time = time()
print(start_time)

# Sets working directory; example below of working directory, change to preferred location
working_directory = r'C:\Users\ianjo\Desktop'

# Sets name of output_folder. Will create this folder in working directory if it doesn't already exist.
output_folder = 'OUTPUTX'

# Path for the first feature class. If stored in a geodatabase, do not include file extension. If it's a shapefile not
# stored in a geodatabase, include the .shp extension.
# fc_one = r'C:\Users\NAME\Documents\ArcGIS\MyProject.gdb\Feature_Class'  # example using FC in geodatabase
# fc_one = r'C:\Users\NAME\Documents\ArcGIS\Feature_Class.shp'  # example using shapefile stored in folder
fc_one = r'D:\ArcGIS Pro projects\Chama\Chama.gdb\TownsSubset'

# Path for the second feature class. Same conventions as for fc_one
fc_two = r'D:\ArcGIS Pro projects\Chama\Chama.gdb\TownsSubset'

# Path to digital elevation model.  Size of the DEM raster is primary determinant for how long it takes to calculate
# each pathdistance and backlink raster. Reducing resolution of DEM, or decreasing size of area covered, will
# decrease runtime. It is especially helpful to clip DEM to only a slightly larger than covers all the locations in
#  fc_one and fc_two.
digital_elevation_model = r'D:\ArcGIS Pro projects\Chama\Chama.gdb\SubsetClip'

# fc_one and fc_two need to have a field with short names for the locations, with a max of four characters. This is due
# to ArcGIS raster naming limitations. These short names will be used to name output files. Set the variables below to
# the name of the column (fieldname) where the short names are stored. If variable does not match the name of the field
# in the feature class exactly, analysis will fail.
fc_one_loc_filename = 'LA_text'  # Change this to name of field in your feature class
fc_two_loc_filename = 'LA_text'  # Change this to name of field in your feature class

# fc_one and fc_two need to have a field with names for the locations.  These names can be longer, but should not
# include spaces or special characters. The output csv and excel tables will use these names to identify the locations
# in each row of the table. You can also reuse the same field used for the filename. Set the variables below to
# the name of the column (fieldname) where the location names are stored. If variable does not match the name of the
# field in the feature class exactly, analysis will fail.
fc_one_loc_name = 'LA_text'  # Change this to name of field in your feature class.
fc_two_loc_name = 'LA_text'  # Change this to name of field in your feature class

# If round_trip = True, once analysis is finished iterating least cost paths from each location in fc_two back to each
# location in fc_one, it will then iterate all least cost paths from fc_one back to fc_two. If round_trip = False, it
# will only calculate paths from locations in fc_two back to locations in fc_one, and the pathdistance and backlink
# rasters will only be calculated for the locations in fc_one. Least cost paths are anisotropic, so you will get
# different costs and different paths depending on which direction of travel is chosen. In many cases, the differences
# are negligible, and there is little utility in iterating in both directions. If you are not calculating in both
# directions, set fc_one to the feature class with the fewer locations, as this will result in decreased runtimes.
round_trip = False

# If set to True, all intermediate files are saved.  This includes the path_distance rasters before they are converted
# to simplified polylines, and individual .csv text files for each iteration between locations. If set to False, the
# costpath rasters and the individual .csv files are not saved. For large analyses, costpath rasters can take up a
# significant amount of hard drive space
int_data = False

# Path to text file with cost_table. Two common approaches measure cost in calories or cost in time (Tobler's
# function). Any table relating a cost value to a slope value is acceptable.
cost_table = r'C:\Users\ianjo\Desktop\ToblerAway.txt'


######### PREPARES DATA AND FILE STRUCTURE - DO NOT EDIT ##########

# Converts cost_table into vertical factor
vertical_factor = VfTable(cost_table)

# Sets workspace to working_directory variable inputted above
arcpy.env.workspace = working_directory

# Sets folder names for output folders
subdir = working_directory + '\\' + output_folder
subdir_fc1 = working_directory + '\\' + output_folder + '\\fc_one_output'
subdir_fc2 = working_directory + '\\' + output_folder + '\\fc_two_output'
folder1, folder2, folder3, folder4, folder5, folder6 = output_folder, 'pathdis', 'backlink', 'polylines', \
                                                       'costpath', 'tables'
# Creates output folders
if fc_one == fc_two or round_trip is False:
    if not arcpy.Exists(folder1):
        print('Creating ' + folder1 + ' and subdirectories in ' + working_directory)
        arcpy.CreateFolder_management(working_directory, folder1)
        arcpy.CreateFolder_management(subdir, folder2)
        arcpy.CreateFolder_management(subdir, folder3)
        arcpy.CreateFolder_management(subdir, folder4)
        if int_data is True:
            arcpy.CreateFolder_management(subdir, folder5)
            arcpy.CreateFolder_management(subdir, folder6)
    else:
        if not arcpy.Exists(subdir + r'\pathdis'):
            arcpy.CreateFolder_management(subdir, folder2)
        if not arcpy.Exists(subdir + r'\backlink'):
            arcpy.CreateFolder_management(subdir, folder3)
        if not arcpy.Exists(subdir + r'\polylines'):
            arcpy.CreateFolder_management(subdir, folder4)
        if int_data is True:
            if not arcpy.Exists(subdir + r'\costpath'):
                arcpy.CreateFolder_management(subdir, folder5)
            if not arcpy.Exists(subdir + r'\tables'):
                arcpy.CreateFolder_management(subdir, folder6)

if fc_one != fc_two and round_trip is True:
    if not arcpy.Exists(folder1):
        print('Creating ' + folder1 + ' and subdirectories in ' + working_directory)
        arcpy.CreateFolder_management(working_directory, folder1)
        arcpy.CreateFolder_management(subdir, '\\fc_one_output')
        arcpy.CreateFolder_management(subdir, '\\fc_two_output')
        arcpy.CreateFolder_management(subdir_fc1, folder2)
        arcpy.CreateFolder_management(subdir_fc2, folder2)
        arcpy.CreateFolder_management(subdir_fc1, folder3)
        arcpy.CreateFolder_management(subdir_fc2, folder3)
        arcpy.CreateFolder_management(subdir_fc1, folder4)
        arcpy.CreateFolder_management(subdir_fc2, folder4)
        arcpy.CreateFolder_management(subdir_fc1, folder5)
        arcpy.CreateFolder_management(subdir_fc2, folder5)
        arcpy.CreateFolder_management(subdir_fc1, folder6)
        arcpy.CreateFolder_management(subdir_fc2, folder6)

    else:
        if not arcpy.Exists(subdir_fc1):
            arcpy.CreateFolder_management(subdir, '\\fc_one_output')
            arcpy.CreateFolder_management(subdir_fc1, folder2)
            arcpy.CreateFolder_management(subdir_fc1, folder3)
            arcpy.CreateFolder_management(subdir_fc1, folder4)
            arcpy.CreateFolder_management(subdir_fc1, folder5)
            arcpy.CreateFolder_management(subdir_fc1, folder6)
        else:
            if not arcpy.Exists(subdir_fc1 + '\\' + folder2):
                arcpy.CreateFolder_management(subdir_fc1, folder2)
            if not arcpy.Exists(subdir_fc1 + '\\' + folder3):
                arcpy.CreateFolder_management(subdir_fc1, folder3)
            if not arcpy.Exists(subdir_fc1 + '\\' + folder4):
                arcpy.CreateFolder_management(subdir_fc1, folder4)
            if not arcpy.Exists(subdir_fc1 + '\\' + folder5):
                arcpy.CreateFolder_management(subdir_fc1, folder5)
            if not arcpy.Exists(subdir_fc1 + '\\' + folder6):
                arcpy.CreateFolder_management(subdir_fc1, folder6)

        if not arcpy.Exists(subdir_fc2):
            arcpy.CreateFolder_management(subdir, '\\fc_two_output')
            arcpy.CreateFolder_management(subdir_fc2, folder2)
            arcpy.CreateFolder_management(subdir_fc2, folder3)
            arcpy.CreateFolder_management(subdir_fc2, folder4)
            arcpy.CreateFolder_management(subdir_fc2, folder5)
            arcpy.CreateFolder_management(subdir_fc2, folder6)
        else:
            if not arcpy.Exists(subdir_fc2 + '\\' + folder2):
                arcpy.CreateFolder_management(subdir_fc2, folder2)
            if not arcpy.Exists(subdir_fc2 + '\\' + folder3):
                arcpy.CreateFolder_management(subdir_fc2, folder3)
            if not arcpy.Exists(subdir_fc2 + '\\' + folder4):
                arcpy.CreateFolder_management(subdir_fc2, folder4)
            if not arcpy.Exists(subdir_fc2 + '\\' + folder5):
                arcpy.CreateFolder_management(subdir_fc2, folder5)
            if not arcpy.Exists(subdir_fc2 + '\\' + folder6):
                arcpy.CreateFolder_management(subdir_fc2, folder6)

if fc_one == fc_two or round_trip is False:
    directory = subdir
else:
    directory = subdir_fc1

# Sets working directory
# working_directory = r'C:\Users\ianjo\Desktop\chama' + '\\' + output_folder  # example of working directory, change to preferred location

# Creates dummy table to store results of each pairwise iteration of the analysis.
table = arcpy.CreateTable_management(directory, 'maintable.dbf')
arcpy.AddField_management(table, 'Source', 'TEXT')
arcpy.AddField_management(table, 'Dest', 'TEXT')
arcpy.AddField_management(table, 'PathCost', 'FLOAT')
arcpy.AddField_management(table, 'Distance', 'FLOAT')

fields = ['Source', 'Dest', 'PathCost', 'Distance']

# Creates log file
log = open(directory + '\log' + str(int(time()))[-8:] + '.txt', 'a+')
log.write('------------------------------------------------------------------------------------------' + '\n')
log.write('Event log for least cost path analysis between locations in: ' + '\n')
log.write(fc_one + '\n')
log.write(fc_two + '\n')
log.write('Event log created: ' + asctime() + '\n')
log.write('------------------------------------------------------------------------------------------' + '\n')


########## START OF ACTUAL ANALYSIS - DO NOT EDIT #########

# Starts analysis, computing pathdistance and backlink rasters for each location in fc_one, and then the cost_path from
# each location in fc_two back to each location in fc_one.
with arcpy.da.SearchCursor(fc_one, [fc_one_loc_name, fc_one_loc_filename]) as cursor:
    for row in cursor:
        loc_one_name = row[0]
        loc_one_filename = row[1]
        print('Calculating path distance and backlink raster for site: ' + loc_one_name)
        arcpy.MakeFeatureLayer_management(fc_one, 'source',
                                          '"{}" = \'{}\''.format(fc_one_loc_filename, loc_one_filename))
        pd_raster = path_distance('source', digital_elevation_model, vertical_factor, loc_one_filename)
        in_cost_backlink_raster = directory + r'\backlink\bl_' + loc_one_filename

        with arcpy.da.SearchCursor(fc_two, [fc_two_loc_name, fc_two_loc_filename]) as cursor:
            for row in cursor:
                start_subtime = time()
                loc_two_name = row[0]
                loc_two_filename = row[1]
                arcpy.MakeFeatureLayer_management(fc_two, 'destination', '"{}" = \'{}\''.format(fc_two_loc_filename,
                                                                                                loc_two_filename))
                if loc_one_name != loc_two_name:
                    out_cost_path = cost_path('destination', pd_raster, in_cost_backlink_raster)
                    convert(out_cost_path, loc_one_filename, loc_two_filename, loc_one_name, loc_two_name)
                    end_subtime = time()
                    subtime = end_subtime - start_subtime
                    print('Finished generating least cost path between ' + loc_one_name + ' and ' + loc_two_name +
                          ' in ' + str(subtime) + ' seconds.')

# The following portion of script runs if feature class 1 and feature class 2 are different and round_trip is set to
# True.  In that case, script repeats entire process from above, swapping feature class 1 and feature class 2, to
# derive all outputs in the reverse direction of travel. If feature class 1 and 2 are identical, there is no reason
# to run process again, as all pairwise combinations, in both directions, are derived from first run
if fc_one != fc_two and round_trip is True:
    directory = subdir_fc2
    with arcpy.da.SearchCursor(fc_two, [fc_two_loc_name, fc_two_loc_filename]) as cursor:
        for row in cursor:
            loc_two_name = row[0]
            loc_two_filename = row[1]
            print('Calculating path distance and backlink raster for site: ' + loc_two_name)
            arcpy.MakeFeatureLayer_management(fc_two, 'source',
                                              '"{}" = \'{}\''.format(fc_two_loc_filename, loc_two_filename))
            pd_raster = path_distance('source', digital_elevation_model, vertical_factor, loc_two_filename)
            in_cost_backlink_raster = directory + r'\backlink\bl_' + loc_two_filename

            with arcpy.da.SearchCursor(fc_one, [fc_one_loc_name, fc_one_loc_filename]) as cursor:
                for row in cursor:
                    start_subtime = time()
                    loc_one_name = row[0]
                    loc_one_filename = row[1]
                    arcpy.MakeFeatureLayer_management(fc_one, 'destination', '"{}" = \'{}\''.format(fc_one_loc_filename,
                                                                                                    loc_one_filename))
                    out_cost_path = cost_path('destination', pd_raster, in_cost_backlink_raster)
                    convert(out_cost_path, loc_two_filename, loc_one_filename, loc_two_name, loc_one_name)
                    end_subtime = time()
                    subtime = end_subtime - start_subtime
                    print('Finished generating least cost path between ' + loc_two_name + ' and ' + loc_one_name +
                          ' in ' + str(subtime) + ' seconds.')

arcpy.MakeTableView_management(table, 'tableview')
arcpy.TableToExcel_conversion('tableview', directory + r'\master.xls')

log.close()
end_time = time()
print(end_time)
time_taken = end_time - start_time  # time_taken is in seconds
print('Script took ' + str(time_taken) + ' seconds to complete.')
