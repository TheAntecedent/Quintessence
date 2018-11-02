from enum import Enum
from sys import float_info

from googleapiclient.discovery import build
from httplib2 import Http
from oauth2client import file, client, tools
import gspread

class BorderTypes(Enum):
  Top = 'top'
  Bottom = 'bottom'
  Left = 'left'
  Right = 'right'
  InnerHorizontal = 'innerHorizontal'
  InnerVertical = 'innerVertical'

class BorderStyle(Enum):
  Dotted = 'DOTTED'
  Dashed = 'DASHED'
  Solid = 'SOLID'
  SolidMedium = 'SOLID_MEDIUM'
  SolidThick = 'SOLID_THICK'
  Double = 'DOUBLE'
  NoBorder = 'NONE'

class RecolorBackgroundConditionalCriteria:
  def __init__(self, hexcode, formula):
    self.format = {
      'backgroundColor': RecolorBackgroundConditionalCriteria.hex2rgb(hexcode)
    }
    self.formula = formula
  
  @staticmethod
  def max(hexcode):
    return RecolorBackgroundConditionalCriteria(hexcode, '=$COL = max($COL)')
  
  @staticmethod
  def greaterThan(hexcode, min_threshold):
    return RecolorBackgroundConditionalCriteria(hexcode, '=$COL >= ' + str(min_threshold))
  
  @staticmethod
  def lessThan(hexcode, max_threshold):
    return RecolorBackgroundConditionalCriteria(hexcode, '=AND($COL > 0, $COL < ' + str(max_threshold) + ')')

  @staticmethod
  def between(hexcode, min_threshold, max_threshold):
    return RecolorBackgroundConditionalCriteria(hexcode, '=AND($COL >= ' + str(min_threshold) + ', $COL <= ' + str(max_threshold) + ')')
  
  @staticmethod
  def hex2rgb(hexcode):
    hexcode = hexcode.lstrip('#')
    rgb = tuple(int(hexcode[i:i+2], 16) for i in (0, 2, 4))
    return {
      'red': rgb[0] / 255.0,
      'green': rgb[1] / 255.0,
      'blue': rgb[2] / 255.0,
    }

def openSpreadsheet(token_filepath, credentials_filepath, scope, spreadsheet_id):
  store = file.Storage(token_filepath)
  credentials = store.get()
  if not credentials or credentials.invalid:
    flow = client.flow_from_clientsecrets(credentials_filepath, scope)
    credentials = tools.run_flow(flow, store)
  
  return gspread.authorize(credentials).open_by_key(spreadsheet_id)

def worksheetExists(spreadsheet, worksheet_name):
  try:
    spreadsheet.worksheet(worksheet_name)
    return True
  except:
    return False

def readAllCells(spreadsheet, worksheet_name):
  try:
    return spreadsheet.worksheet(worksheet_name).get_all_values()
  except:
    # the worksheet doesn't exist, so return no data
    return [[]]
  
def createUpdateColumnSizeRequest(worksheet, col_index_start, num_cols, pixelSize):
  return {
    'updateDimensionProperties': {
      'range': {
        'sheetId': worksheet.id,
        'dimension': 'COLUMNS',
        'startIndex': col_index_start,
        'endIndex': col_index_start + num_cols
      },
      'properties': {
        'pixelSize': pixelSize
      },
      'fields': 'pixelSize'
    }
  }
  
def createFormatCellsRequest(worksheet, row_index_start, col_index_start, num_rows, num_cols, props):
  fields = ','.join(
    'userEnteredFormat/%s' % p for p in props.keys()
  )
  return {
    'repeatCell': {
      'range': {
        'sheetId': worksheet.id,
        'startRowIndex': row_index_start,
        'startColumnIndex': col_index_start,
        'endRowIndex': row_index_start + num_rows,
        'endColumnIndex': col_index_start + num_cols
      },
      'cell': {
        'userEnteredFormat': props
      },
      'fields': fields
    }
  }

def createUpdateGridPropertiesRequest(worksheet, grid_properties):
  fields = ','.join(
    'gridProperties/%s' % p for p in grid_properties.keys()
  )
  return {
    'updateSheetProperties': {
      'properties': {
        'sheetId': worksheet.id,
        'gridProperties': grid_properties
      },
      'fields': fields
    }
  }

def createConditionalFormattingRuleForColumn(worksheet, col_index, rule_index, formula, format):
  return {
    'addConditionalFormatRule': {
      'rule': {
        'range': {
          'sheetId': worksheet.id,
          'startRowIndex': 1,
          'startColumnIndex': col_index,
          'endColumnIndex': col_index + 1
        },
        'booleanRule': {
          'condition': {
            'type': 'CUSTOM_FORMULA',
            'values': [{
              'userEnteredValue': formula
            }]
          },
          'format': format
        }
      },
      'index': rule_index
    }
  }

def createAllConditionalFormattingRulesForColumn(worksheet, col_index, criteria):
  col_letter_name = chr(ord('A') + col_index)
  col_text = col_letter_name + ':' + col_letter_name

  request_range = {
    'sheetId': worksheet.id,
    'startRowIndex': 1,
    'startColumnIndex': col_index,
    'endColumnIndex': col_index + 1,
  }

  return [
    {
      'addConditionalFormatRule': {
        'rule': {
          'ranges': request_range,
          'booleanRule': {
            'condition': {
              'type': 'CUSTOM_FORMULA',
              'values': [{ 'userEnteredValue': criterion.formula.replace('$COL', col_text) }]
            },
            'format': criterion.format
          }
        },
        'index': i,
      }
    }
    for i, criterion in enumerate(criteria)
  ]

def createUpdateBorders(worksheet, row_index_start, col_index_start, num_rows, num_cols, border_types, border_style, color = None):
  request = {
    'updateBorders': {
      'range': {
        'sheetId': worksheet.id,
        'startRowIndex': row_index_start,
        'startColumnIndex': col_index_start,
        'endRowIndex': row_index_start + num_rows,
        'endColumnIndex': col_index_start + num_cols
      },
    }
  }

  border_payload = {
    'style': border_style.value
  }
  if color:
    border_payload['color'] = color
  for border_type in border_types:
    request['updateBorders'][border_type.value] = border_payload

  return request

def writeToWorksheetOverwriting(spreadsheet, worksheet_name, data):
  num_rows = len(data)
  num_cols = max([len(row) for row in data])

  # get a clean worksheet
  try:
    worksheet = spreadsheet.worksheet(worksheet_name)
    spreadsheet.del_worksheet(worksheet)
  except:
    pass
  
  worksheet = spreadsheet.add_worksheet(worksheet_name, num_rows, num_cols)

  all_cells = worksheet.range(1, 1, num_rows + 1, num_cols + 1)
  for cell in all_cells:
    # if there is data for the cell, update it
    if cell.row - 1 < len(data) and cell.col - 1 < len(data[cell.row - 1]):
      cell.value = str(data[cell.row - 1][cell.col - 1]) 
  
  worksheet.update_cells(all_cells, 'USER_ENTERED')

def formatWorksheet(spreadsheet, worksheet_name, data, num_player_stat_cols, num_core_player_stat_cols):
  num_rows = len(data)
  num_cols = num_player_stat_cols
  worksheet = spreadsheet.worksheet(worksheet_name)

  # 1. freeze the header row & col
  freeze_cells = createUpdateGridPropertiesRequest(worksheet, {
    'frozenRowCount': 1,
    'frozenColumnCount': 1
  })

  # 2. format the title row
  format_title_row = createFormatCellsRequest(worksheet, 0, 0, 1, num_cols, {
    'textFormat': {
      'bold': True
    }
  })
  resize_column_widths_p1 = createUpdateColumnSizeRequest(worksheet, 0, num_core_player_stat_cols, 200)
  resize_column_widths_p2 = createUpdateColumnSizeRequest(worksheet, num_core_player_stat_cols, num_cols - num_core_player_stat_cols, 200)

  # 3. format all core stat text
  format_core_stat_text = createFormatCellsRequest(worksheet, 1, 1, num_rows - 1, num_cols - 1, {
    'horizontalAlignment': 'CENTER',
  })

  # 4. add a separator between the core & auxiliary stats
  core_aux_stat_border = createUpdateBorders(worksheet, 0, num_core_player_stat_cols - 1, num_rows, 1, [BorderTypes.Right], BorderStyle.SolidThick)

  # 5. create conditional formatting rules
  # 5.a. conditional formatting rules for core stats
  BEST_COLOR = '#00ffff'
  GOOD_COLOR = '#b7ffcd'
  AVERAGE_COLOR = '#fce8b2'
  SUBPAR_COLOR = '#f4c7c3'

  core_stat_dpm_formatting = createAllConditionalFormattingRulesForColumn(worksheet, 2, [
    RecolorBackgroundConditionalCriteria.max(BEST_COLOR),
    RecolorBackgroundConditionalCriteria.greaterThan(GOOD_COLOR, 300),
    RecolorBackgroundConditionalCriteria.between(AVERAGE_COLOR, 200, 300),
    RecolorBackgroundConditionalCriteria.lessThan(SUBPAR_COLOR, 200),
  ])
  core_stat_hpm_formatting = createAllConditionalFormattingRulesForColumn(worksheet, 4, [
    RecolorBackgroundConditionalCriteria.max(BEST_COLOR),
    RecolorBackgroundConditionalCriteria.greaterThan(GOOD_COLOR, 950),
    RecolorBackgroundConditionalCriteria.between(AVERAGE_COLOR, 850, 950),
    RecolorBackgroundConditionalCriteria.lessThan(SUBPAR_COLOR, 850),
  ])
  core_stat_win_rate_formatting = createAllConditionalFormattingRulesForColumn(worksheet, 5, [
    RecolorBackgroundConditionalCriteria.max(BEST_COLOR),
    RecolorBackgroundConditionalCriteria.greaterThan(GOOD_COLOR, 0.6),
    RecolorBackgroundConditionalCriteria.between(AVERAGE_COLOR, 0.4, 0.6),
    RecolorBackgroundConditionalCriteria.lessThan(SUBPAR_COLOR, 0.4),
  ])

  # 5.b. conditional formatting rules for auxiliary stats
  aux_stat_dpm_formatting_unflattened = [
    createAllConditionalFormattingRulesForColumn(worksheet, num_core_player_stat_cols + i, [
      RecolorBackgroundConditionalCriteria.max(BEST_COLOR),
      RecolorBackgroundConditionalCriteria.greaterThan(GOOD_COLOR, 300),
      RecolorBackgroundConditionalCriteria.between(AVERAGE_COLOR, 200, 300),
      RecolorBackgroundConditionalCriteria.lessThan(SUBPAR_COLOR, 200),
    ])
    for i in range(num_cols - num_core_player_stat_cols)
  ]
  aux_stat_dpm_formatting = [item for sublist in aux_stat_dpm_formatting_unflattened for item in sublist]

  # 5.z. consolidate into a single list of conditional formatting rules
  conditional_formatting_rules = core_stat_dpm_formatting + core_stat_hpm_formatting + core_stat_win_rate_formatting + aux_stat_dpm_formatting
  
  # Finally, send format request
  spreadsheet.batch_update({
    'requests': [
      freeze_cells,
      format_title_row,
      format_core_stat_text,
      resize_column_widths_p1,
      resize_column_widths_p2,
      core_aux_stat_border
    ] + conditional_formatting_rules
  })
